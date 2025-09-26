import argparse
import hashlib
import re
import sys
import html
import os

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Required library not found.")
    print("Please install BeautifulSoup4 and lxml by running: pip install beautifulsoup4 lxml")
    sys.exit(1)

def load_salt(filename="salt"):
    """Loads the full salt string from an external file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            full_salt = f.read().strip()
            if not full_salt:
                print(f"Error: The salt file '{filename}' is empty.")
                sys.exit(1)
            return full_salt
    except FileNotFoundError:
        print(f"Error: The required salt file '{filename}' was not found in the same directory.")
        print("Please create a file named 'salt' containing the full encryption string.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading the salt file '{filename}': {e}")
        sys.exit(1)

# Load the full salt string from the external "salt" file.
_FULL_ENCRYPT_STRING = load_salt()
# Slice the loaded string to get the specific salt for checksums.
CHECKSUM_SALT = _FULL_ENCRYPT_STRING[64:64+97]

def calculate_checksum(data: str) -> str:
    """Calculates the MD5 checksum for the save data payload."""
    salted_data = (data + CHECKSUM_SALT).encode('utf-8')
    hash = hashlib.md5(salted_data).hexdigest()
    print("hash",hash)
    print("size",len(data))
    print("head",data[0:20])
    print("tail",data[-20:])
    return hash

def find_save_node(soup):
    """Finds the data node by looking for text starting with a 32-char hex string."""
    checksum_pattern = re.compile(r'^\s*[a-f0-9]{32}', re.IGNORECASE)
    tag = soup.find(string=checksum_pattern)
    return tag

def decode_save(in_file: str, out_txt: str, out_template: str):
    """Decodes a .sav file into a readable .txt and a .tpl template file."""
    print(f"--> Decoding '{in_file}'...")
    try:
        with open(in_file, 'r', encoding='utf-8-sig') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found at '{in_file}'")
        sys.exit(1)

    soup = BeautifulSoup(content, 'lxml-xml')
    save_string_node = find_save_node(soup)
    
    if not save_string_node:
        print("Error: Could not find the core save data string within the file.")
        sys.exit(1)

    save_data_block_from_parser = save_string_node.string
    full_save_string = save_data_block_from_parser.strip()
    original_checksum = full_save_string[:32]
    data_payload = full_save_string[32:]

    expected_checksum = calculate_checksum(data_payload)
    print(f"    Original Checksum: {original_checksum}")
    if original_checksum.lower() == expected_checksum.lower():
        print("    Checksum is valid.")
    else:
        print(f"    Warning: Checksum is INVALID! (Expected: '{expected_checksum}')")

    clean_payload = html.unescape(data_payload)

    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(f"# Rain World Save - Readable Format\n")
        f.write(f"# Original Checksum: {original_checksum}\n\n")
        formatted_payload = re.sub(r'(<[^>]+A>)', r'\1\n', clean_payload)
        f.write(formatted_payload)
    print(f"--> Successfully created readable save data at '{out_txt}'")

    #template_content = content.replace(save_data_block_from_parser, '{SAVESTRING}')

    # 1. Find the starting index of the save data using the unique checksum we found.
    #    We search within the original, raw 'content' string.
    start_index = content.find(original_checksum)
    if start_index == -1:
        print("\n--- CRITICAL ERROR ---")
        print("Failed to locate the checksum in the raw file content. Cannot create template.")
        sys.exit(1)

    # 2. Find the index of the first closing '</anyType>' tag that appears *after* the checksum.
    #    This reliably marks the end of the data block we need to replace.
    end_marker = '&gt;</anyType></Values></ArrayOfKeyValueOfanyTypeanyType>'
    end_index = content.find(end_marker, start_index)+4
    if end_index == -1:
        print("\n--- CRITICAL ERROR ---")
        print(f"Failed to locate the end marker ('{end_marker}') in the raw file content. Cannot create template.")
        sys.exit(1)
    print("s",start_index)
    print("e",end_index)
    # 3. Rebuild the file content by slicing the original string and inserting the placeholder.
    #    This is the most robust method possible.
    prefix = content[:start_index]
    # The suffix starts at the beginning of the end_marker, preserving it.
    suffix = content[end_index:]
    template_content = prefix + '{SAVESTRING}' + suffix

    with open(out_template, 'w', encoding='utf-8-sig') as f:
        f.write(template_content)
    print(f"--> Successfully created template file at '{out_template}'")

def encode_save(in_txt: str, in_template: str, out_file: str):
    """Encodes a .txt and a .tpl file back into a game-ready .sav file."""
    print(f"--> Encoding from '{in_txt}' and '{in_template}'...")
    try:
        with open(in_txt, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        with open(in_template, 'r', encoding='utf-8-sig') as f:
            template_content = f.read()
    except FileNotFoundError as e:
        print(f"Error: An input file was not found: {e.filename}")
        sys.exit(1)

    tokens = []
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line.startswith("#") and stripped_line:
            tokens.append(stripped_line)
    data_payload = "".join(tokens)

    new_checksum = calculate_checksum(data_payload)
    data_payload = html.escape(data_payload)
    print(f"    New checksum calculated: {new_checksum}")
    new_full_save_string = new_checksum + data_payload

    final_content = template_content.replace('{SAVESTRING}', new_full_save_string)

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print(f"--> Successfully encoded new save file to '{out_file}'")

def main():
    parser = argparse.ArgumentParser(
        description="A robust tool to convert Rain World save files to a readable format and back.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Workflow:

1. Decode your save file.
   - This creates two files: a `.txt` for editing and a `.tpl` for structure.
   - If output filenames aren't given, they are created automatically from the input name.
   
   Example: python rwsave.py -d my_save.sav

2. Edit the generated `.txt` file.

3. Encode your changes back into a new save file.
   - You must provide the edited text file and the generated template file.
   
   Example: python rwsave.py -e my_save.sav.txt my_save.sav.tpl new_save.sav
"""
    )
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument('-d', '--decode', dest='infile', metavar='INFILE',
                               help="DECODE a .sav file into a .txt and .tpl file.")
    command_group.add_argument('-e', '--encode', dest='infiles', nargs=2, metavar=('IN_TXT', 'IN_TPL'),
                               help="ENCODE a .txt and .tpl file into a new .sav file.")

    parser.add_argument('outfiles', nargs='*', help="[Optional] Output file paths. See usage for details.")
    
    args = parser.parse_args()

    if args.infile: # Decode Mode
        if len(args.outfiles) >= 2:
            out_txt, out_template = args.outfiles[0], args.outfiles[1]
        elif len(args.outfiles) == 1:
            out_txt = args.outfiles[0]
            out_template = f"{os.path.normpath(args.infile)}.tpl"
        else:
            out_txt = f"{os.path.normpath(args.infile)}.txt"
            out_template = f"{os.path.normpath(args.infile)}.tpl"
        decode_save(args.infile, out_txt, out_template)

    elif args.infiles: # Encode Mode
        in_txt, in_template = args.infiles
        if args.outfiles:
            outfile = args.outfiles[0]
        else:
            base_name = os.path.normpath(in_txt).rsplit('.', 1)[0]
            outfile = f"{base_name}_new.sav"
        encode_save(in_txt, in_template, outfile)

if __name__ == "__main__":
    main()