from flask import Flask, request, send_file
import subprocess
import tempfile
import os
import uuid

app = Flask(__name__)

UPLOAD_DIR = '/tmp/conversions'
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route('/api/convert/epub-to-pdf', methods=['POST'])
def epub_to_pdf():
    if 'file' not in request.files:
        return {'error': 'No file uploaded'}, 400

    file = request.files['file']
    if not file.filename.endswith('.epub'):
        return {'error': 'File must be .epub'}, 400

    job_id = str(uuid.uuid4())[:8]
    epub_path = os.path.join(UPLOAD_DIR, f'{job_id}.epub')
    pdf_path = os.path.join(UPLOAD_DIR, f'{job_id}.pdf')

    try:
        file.save(epub_path)

        # Get optional settings
        page_size = request.form.get('page_size', 'a4')
        margin = request.form.get('margin', '15')
        font_size = request.form.get('font_size', '13')

        # Run Calibre's ebook-convert
        cmd = [
            'ebook-convert', epub_path, pdf_path,
            '--paper-size', page_size,
            '--pdf-default-font-size', font_size,
            '--pdf-page-margin-left', margin,
            '--pdf-page-margin-right', margin,
            '--pdf-page-margin-top', margin,
            '--pdf-page-margin-bottom', margin,
            '--pdf-add-toc',
            '--pdf-page-numbers',
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            return {'error': 'Conversion failed', 'detail': result.stderr[-500:]}, 500

        if not os.path.exists(pdf_path):
            return {'error': 'PDF was not generated'}, 500

        # Build output filename
        out_name = file.filename.rsplit('.', 1)[0] + '.pdf'

        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=out_name
        )

    finally:
        # Cleanup
        for p in [epub_path, pdf_path]:
            try:
                os.remove(p)
            except OSError:
                pass


@app.route('/api/health', methods=['GET'])
def health():
    return {'status': 'ok'}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
