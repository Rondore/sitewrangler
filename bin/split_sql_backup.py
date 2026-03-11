#!/usr/bin/env python3

def extract_databases(filename: str, output_dir: str):
    with open(filename, 'r', encoding = "ISO-8859-1") as input_file:
        line_number = 0
        output_writer = None
        header = ''
        for line in input_file:
            line_number += 1
            clean_line = line.strip()
            if clean_line.startswith('-- Current Database: `'):
                db_name = clean_line[len('-- Current Database: `'):-1]
                output_file = f"{output_dir}/{db_name}.sql"
                if(output_writer):
                    output_writer.close()
                output_writer = open(output_file, 'w', encoding = "ISO-8859-1")
                output_writer.write(header)
            if output_writer:
                output_writer.write(line)
            else:
                header += line
        if output_writer:
            output_writer.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Extract databases from a SQL dump file.')
    parser.add_argument('source_file', help='The SQL dump file to process.')
    parser.add_argument('output_dir', help='The directory to save the extracted database files.')
    
    args = parser.parse_args()
    
    extract_databases(args.source_file, args.output_dir)
