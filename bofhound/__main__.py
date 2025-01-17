import sys
import logging
import typer
import glob
import os
from bofhound.parsers import LdapSearchBofParser
from bofhound.writer import BloodHoundWriter
from bofhound.ad import ADDS
from bofhound import console

app = typer.Typer(add_completion=False)

@app.command()
def main(
    input_files: str = typer.Option("/opt/cobaltstrike/logs", "--input", "-i", help="Directory or file containing logs of ldapsearch results"),
    output_folder: str = typer.Option(".", "--output", "-o", help="Location to export bloodhound files"),
    all_properties: bool = typer.Option(False, "--all-properties", "-a", help="Write all properties to BloodHound files (instead of only common properties)"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
    zip_files: bool = typer.Option(False, "--zip", "-z", help="Compress the JSON output files into a zip archive")):
    """
    Generate BloodHound compatible JSON from logs written by ldapsearch BOF and pyldapsearch
    """

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    banner()

    if os.path.isfile(input_files):
        cs_logs = [input_files]
        logging.debug(f"Log file explicitly provided {input_files}")
    elif os.path.isdir(input_files):
        # recurisively get a list of all .log files in the input directory, sorted by last modified time
        cs_logs = glob.glob(f"{input_files}/**/beacon*.log", recursive=True)
        if len(cs_logs) == 0:
            # check for ldapsearch python logs
            cs_logs = glob.glob(f"{input_files}/pyldapsearch*.log", recursive=True)

        cs_logs.sort(key=os.path.getmtime)

        if len(cs_logs) == 0:
            logging.error(f"No log files found in {input_files}!")
            return
        else:
            logging.info(f"Located {len(cs_logs)} beacon log files")
    else:
        logging.error(f"Could not find {input_files} on disk")
        sys.exit(-1)

    parsed_objects = []
    with console.status(f"", spinner="aesthetic") as status:
        for log in cs_logs:
            status.update(f" [bold] Parsing {log}")
            new_objects = LdapSearchBofParser.parse_file(log)
            logging.debug(f"Parsed {log}")
            logging.debug(f"Found {len(new_objects)} objects in {log}")
            parsed_objects.extend(new_objects)


    logging.info(f"Parsed {len(parsed_objects)} objects from {len(cs_logs)} log files")

    ad = ADDS()

    logging.info("Sorting parsed objects by type...")
    ad.import_objects(parsed_objects)

    logging.info(f"Parsed {len(ad.users)} Users")
    logging.info(f"Parsed {len(ad.groups)} Groups")
    logging.info(f"Parsed {len(ad.computers)} Computers")
    logging.info(f"Parsed {len(ad.domains)} Domains")
    logging.info(f"Parsed {len(ad.trustaccounts)} Trust Accounts")
    logging.info(f"Parsed {len(ad.schemas)} Schemas")
    logging.info(f"Parsed {len(ad.unknown_objects)} Unknown Objects")

    ad.process()

    BloodHoundWriter.write(
        output_folder,
        domains=ad.domains,
        computers=ad.computers,
        users=ad.users,
        groups=ad.groups,
        common_properties_only=(not all_properties),
        zip_files=zip_files
    )


def banner():
    print('''
 _____________________________ __    __    ______    __    __   __   __   _______
|   _   /  /  __   / |   ____/|  |  |  |  /  __  \\  |  |  |  | |  \\ |  | |       \\
|  |_)  | |  |  |  | |  |__   |  |__|  | |  |  |  | |  |  |  | |   \|  | |  .--.  |
|   _  <  |  |  |  | |   __|  |   __   | |  |  |  | |  |  |  | |  . `  | |  |  |  |
|  |_)  | |  `--'  | |  |     |  |  |  | |  `--'  | |  `--'  | |  |\   | |  '--'  |
|______/   \\______/  |__|     |__|  |___\\_\\________\\_\\________\\|__| \\___\\|_________\\

                              by Fortalice ✪
    ''')


if __name__ == "__main__":
    app(prog_name="bofhound")
