import os
import PyPDF2
from flask import Flask, render_template, request, redirect, url_for, session,jsonify
from flask_session import Session
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import multiprocessing as mp
import cv2
import numpy as np

app = Flask(__name__)
app.config['PDF_file'] = 'PDF_file/'
app.config['static'] = 'static/'
app.config['split'] = 'split/'
app.config['crop'] = 'crop/'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.config["SECRET_KEY"]="my key"

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'

ocr_results={}

@app.route('/')
def index():
    deleteFile("PDF_file")
    deleteFile("split")
    deleteFile("static")
    return render_template('home_pop.html')

@app.route('/homepage')
def homepage():
    return render_template('home_pop.html')


@app.route('/region_selection')
def region_selection():
    filename = request.args.get('filename')
    return render_template('index.html', filename=filename)

def deleteFile(fileName):
    mypath = fileName
    for root, dirs, files in os.walk(mypath):
        for file in files:
            os.remove(os.path.join(root, file))

def splitPDF():
    filename_list = []
    input_path = os.listdir(app.config['PDF_file'])
    for i, filename in enumerate(input_path):
        if filename.split(".")[-1] == 'pdf':
            pdf_file = os.path.join(app.config['PDF_file'], filename)
            with open(pdf_file, 'rb') as file:
                pdf_reader = PdfReader(file)
                num_pages = len(pdf_reader.pages)
                #num_pages=len(pdf_reader.pages)
                for page_number in range(num_pages):
                    pdf_writer = PdfWriter()
                    # page = pdf_reader.getPage(page_number)
                    page=pdf_reader.pages[page_number]
                    # pdf_writer.addPage(page)
                    pdf_writer.add_page (page)
                    output_path = app.config['split']
                    page_output_path = f"{output_path}_{page_number+1}.pdf"

                    # Write the page to the output PDF file
                    with open(page_output_path, 'wb') as output_file:
                        pdf_writer.write(output_file)
                    filename = f"Page {page_number+1} saved as {page_output_path}"
                    filename_list.append(filename)
    return filename_list

def convert2image():
    filenames = os.listdir(app.config['split'])
    image_filenames = []
    for i, filename in enumerate(filenames):
        if filename.split(".")[-1] == 'pdf':
            image_filename = filename.split(".")[0]
            file_ext = image_filename + ".jpg"
            image_filenames.append(file_ext)
            # Store Pdf with convert_from_path function
            split_filepath = os.path.join(app.config['split'], filename)
            imag = convert_from_path(split_filepath, poppler_path=r'C:\inetpub\wwwroot\ROI\poppler-0.68.0\bin')
            image_path = os.listdir(app.config['static'])
            image_path_final = os.path.join(app.config['static'], file_ext)
            for image in imag:
                image.save(image_path_final, "JPEG", optimize=True, quality=35)
                image_url = image_path_final
            image_filenames = sorted(image_filenames)
    return image_filenames

@app.route('/process_pdf', methods=['POST'])
def process_pdf():
    # Get the uploaded PDF file
    pdf_file = request.files['pdf_file']

    # Specify the destination directory
    destination_directory = app.config['PDF_file']

    # Save the PDF file to the destination directory
    pdf_file.save(os.path.join(destination_directory, pdf_file.filename))
    #split the pdf with the function splitPDF() and wrap it with multiprocessing
    pool1 = mp.Pool(mp.cpu_count())
    output_filepath = pool1.apply_async(splitPDF())

    #convert each pdf to image with the function convert2image() and wrap it with multiprocessing
    pool2 = mp.Pool(mp.cpu_count())
    image_filenames = pool2.apply_async(convert2image())
    files = os.listdir(app.config['static'])
    return render_template('home_pop.html', files=files)

@app.route('/perform_ocr', methods=['POST'])
def perform_ocr():
    
    region_data = request.json
    filename = region_data['filename']
    startX = region_data['startX']
    startY = region_data['startY']
    endX = region_data['endX']
    endY = region_data['endY']

    # Load the image
    image_path = os.path.join(app.config['static'], filename)
    

    region_ocr_text = perform_ocr_on_region(image_path, startX, startY, endX, endY)
    

    return {'text': region_ocr_text}

def perform_ocr_on_region(image_path, startX, startY, endX, endY):
    # Load the image
    image = Image.open(image_path)

    # Crop the image based on the region coordinates
    region = image.crop((startX, startY, endX, endY))

    # Convert region to grayscale
    region = region.convert('L')

    # Denoise the image
    denoised_image = cv2.fastNlMeansDenoising(np.array(region), h=10)
    # Dilate the image
    kernel = np.ones((2, 2), np.uint8)
    dilated_image = cv2.dilate(denoised_image, kernel, iterations=1)



    # Convert the processed image back to PIL Image
    processed_region = Image.fromarray(dilated_image)

    # Perform OCR on the processed region
    ocr_text = pytesseract.image_to_string(processed_region)
    
    ocr_results = {
        'text': ocr_text,
        'coordinates': {
            'startX': startX,
            'startY': startY,
            'endX': endX,
            'endY': endY
        }
    }

    print(ocr_results)
    return ocr_text


@app.route('/process_table', methods=['POST'])
def process_table():
    table_data = request.get_json()
    #print("Name : ",table_data['Name'])
    # Process the table data as needed
    # You can perform any required operations here
    session['table_data'] = table_data
    return redirect(url_for('get_data'))

@app.route('/data')
def get_data():
    table_data = session.get('table_data')
    #print("Name2 : ",table_data['Name'])
    # Process the data as needed
    return render_template("report.html",table_data=table_data)



if __name__ == '__main__':
    app.run()