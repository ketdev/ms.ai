from PIL import Image
import numpy as np

def image_to_cpp_byte_array(img_path, output_file):
    # Load image using PIL
    img = Image.open(img_path)
    img_np = np.array(img)  # Convert image to numpy array

    height, width, channels = img_np.shape

    # Convert image data to a list of bytes
    img_data = img_np.tobytes()

    # Create the C++ array
    cpp_array = "unsigned char pixel_data[{length}] = {{\n".format(length=len(img_data))
    for i, byte in enumerate(img_data):
        cpp_array += "0x{0:02x}, ".format(byte)
        if (i + 1) % 12 == 0:  # Formatting: new line every 12 bytes
            cpp_array += "\n"
    cpp_array = cpp_array.rstrip(", \n") + "\n};\n"

    # Combine everything to be written to the output file
    output_data = f"// Image dimensions: width = {width}, height = {height}, channels = {channels}\n"
    output_data += "// To create cv::Mat in C++:\n"
    output_data += f"// cv::Mat img({height}, {width}, CV_8UC{channels}, pixel_data);\n"
    output_data += cpp_array

    # Write to the output file
    with open(output_file, 'w') as f:
        f.write(output_data)

    print(f"Data written to {output_file}")

image_path = "./capp/assets/player_template.png"
output_cpp_path = "./capp/assets/player_template_data.hpp"
image_to_cpp_byte_array(image_path, output_cpp_path)

