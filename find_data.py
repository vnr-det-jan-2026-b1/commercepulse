import os
import glob

def find_file():
    print("Searching for commercepulse_testdata.xlsx...")
    for root, dirs, files in os.walk(r"c:\projects\commercepulse"):
        for file in files:
            if "testdata.xlsx" in file or "testdata" in file:
                print(f"Found: {os.path.join(root, file)}")

if __name__ == "__main__":
    find_file()
