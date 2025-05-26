import csv
from glob import glob


def load_data():
    data = []
    for filepath in glob('data/*.tsv'):
        with open(filepath, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter='\t')
            for row in reader:
                data.append(row)

    print(f"Loaded {len(data)} total rows.")
    return data


def main():
    data = load_data()
    # Here you can process the data as needed
    # For example, print the first 5 rows
    for row in data[:5]:
        print(row)


if __name__ == "__main__":
    main()