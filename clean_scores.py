from rembg import remove
from PIL import Image
import os


def clean_images():
    # Folder where your 1.png, 2.png... are located
    input_dir = 'assets/scores'
    output_dir = 'assets/scores/clean'

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"🧹 Cleaning images in {input_dir}...")

    files = [f for f in os.listdir(input_dir) if f.lower().endswith('.png')]

    for filename in files:
        inp_path = os.path.join(input_dir, filename)
        out_path = os.path.join(output_dir, filename)

        print(f"   ✨ Processing {filename}...")

        try:
            with open(inp_path, 'rb') as i:
                with open(out_path, 'wb') as o:
                    input_data = i.read()
                    # This magic function removes the background (including checkerboards)
                    output_data = remove(input_data)
                    o.write(output_data)
        except Exception as e:
            print(f"   ❌ Error processing {filename}: {e}")

    print("\n✅ Done! Move the files from 'assets/scores/clean' to 'assets/scores' to use them.")


if __name__ == "__main__":
    clean_images()
