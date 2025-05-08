import os
import pandas as pd
import glob

def list_files(directory):
    """List all files in the given directory and subdirectories."""
    all_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files

def view_csv(file_path, num_rows=5):
    """View the first few rows of a CSV file."""
    try:
        # Try different encodings
        for encoding in ['utf-8', 'latin1', 'cp1252']:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Error reading {file_path} with encoding {encoding}: {e}")
                return None
        
        print(f"\n{'='*80}")
        print(f"File: {file_path}")
        print(f"Shape: {df.shape} (rows, columns)")
        print(f"Columns: {df.columns.tolist()}")
        print("\nData types:")
        print(df.dtypes)
        print("\nSample data:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(df.head(num_rows))
        print(f"{'='*80}\n")
        return df
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

if __name__ == "__main__":
    dataset_dir = "Dataset"
    
    print("Listing all files in Dataset directory:")
    files = list_files(dataset_dir)
    
    csv_files = [f for f in files if f.endswith('.csv')]
    print(f"Found {len(csv_files)} CSV files:")
    for file in csv_files:
        print(f"- {file}")
    
    print("\nDisplaying CSV file contents:")
    for file in csv_files:
        view_csv(file) 