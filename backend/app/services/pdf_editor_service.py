
from pathlib import Path
from uuid import uuid4
import pymupdf


# --------------------------------------------------
# BASIC PDF HELPERS
# --------------------------------------------------

def open_pdf(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError("PDF file not found.")

    if file_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    return pymupdf.open(str(file_path))


def validate_page(pdf, page_number):
    """
    Page numbers are 1-based.
    Example: page_number=1 means the first page.
    """
    if page_number < 1 or page_number > len(pdf):
        raise ValueError("Invalid page number.")

    return pdf[page_number - 1]


def save_pdf(pdf, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        output_path = output_path.with_name(
            f"{output_path.stem}_{uuid4().hex[:8]}{output_path.suffix}"
        )

    pdf.save(
        str(output_path),
        garbage=4,
        deflate=True
    )

    return str(output_path)


# --------------------------------------------------
# PDF INFORMATION
# --------------------------------------------------

def get_pdf_info(file_path):
    pdf = open_pdf(file_path)

    try:
        pages = []

        for index, page in enumerate(pdf):
            images = []

            for image in page.get_images(full=True):
                xref = image[0]

                for rect in page.get_image_rects(xref):
                    images.append({
                        "xref": xref,
                        "x": rect.x0,
                        "y": rect.y0,
                        "width": rect.width,
                        "height": rect.height
                    })

            pages.append({
                "page_number": index + 1,
                "width": page.rect.width,
                "height": page.rect.height,
                "text": page.get_text(),
                "images": images
            })

        return {
            "page_count": len(pdf),
            "metadata": pdf.metadata,
            "pages": pages
        }

    finally:
        pdf.close()


# --------------------------------------------------
# TEXT OPERATIONS
# --------------------------------------------------

def add_text(file_path, output_path, page_number, x, y, text,
             font_size=12, color=(0, 0, 0)):

    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)

        page.insert_text(
            (float(x), float(y)),
            str(text),
            fontsize=float(font_size),
            color=color
        )

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


def replace_text(file_path, output_path, page_number,
                 old_text, new_text, font_size=11):

    if not old_text:
        raise ValueError("Text to replace cannot be empty.")

    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)

        matches = page.search_for(old_text)

        if not matches:
            raise ValueError("The requested text was not found.")

        # Remove the original text.
        for rect in matches:
            page.add_redact_annot(rect, fill=(1, 1, 1))

        page.apply_redactions()

        # Insert replacement text into the old text area.
        for rect in matches:
            page.insert_textbox(
                rect,
                str(new_text),
                fontsize=float(font_size),
                fontname="helv",
                color=(0, 0, 0),
                align=0
            )

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


def delete_text(file_path, output_path, page_number, text):
    if not text:
        raise ValueError("Text cannot be empty.")

    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)
        matches = page.search_for(text)

        if not matches:
            raise ValueError("The requested text was not found.")

        for rect in matches:
            page.add_redact_annot(rect, fill=(1, 1, 1))

        page.apply_redactions()

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


# --------------------------------------------------
# IMAGE OPERATIONS
# --------------------------------------------------

def insert_image(file_path, output_path, page_number,
                 image_path, x, y, width, height):

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError("Image file not found.")

    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)

        rect = pymupdf.Rect(
            float(x),
            float(y),
            float(x) + float(width),
            float(y) + float(height)
        )

        if not page.rect.contains(rect):
            raise ValueError("Image position is outside the page.")

        page.insert_image(
            rect,
            filename=str(image_path),
            keep_proportion=True
        )

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


def replace_image(file_path, output_path, page_number,
                  xref, new_image_path):

    new_image_path = Path(new_image_path)

    if not new_image_path.exists():
        raise FileNotFoundError("Replacement image not found.")

    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)

        image_exists = any(
            image[0] == int(xref)
            for image in page.get_images(full=True)
        )

        if not image_exists:
            raise ValueError("Image not found on this page.")

        page.replace_image(
            int(xref),
            filename=str(new_image_path)
        )

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


def delete_image(file_path, output_path, page_number, xref):
    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)

        image_exists = any(
            image[0] == int(xref)
            for image in page.get_images(full=True)
        )

        if not image_exists:
            raise ValueError("Image not found on this page.")

        page.delete_image(int(xref))

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


# --------------------------------------------------
# ANNOTATIONS
# --------------------------------------------------

def add_comment(file_path, output_path, page_number,
                x, y, text):

    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)

        page.add_text_annot(
            (float(x), float(y)),
            str(text)
        )

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


def add_text_box(file_path, output_path, page_number,
                 x, y, width, height, text,
                 font_size=12):

    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)

        rect = pymupdf.Rect(
            float(x),
            float(y),
            float(x) + float(width),
            float(y) + float(height)
        )

        if not page.rect.contains(rect):
            raise ValueError("Text box is outside the page.")

        page.add_freetext_annot(
            rect,
            str(text),
            fontsize=float(font_size),
            fontname="Helv",
            text_color=(0, 0, 0),
            fill_color=None
        )

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


def add_signature(file_path, output_path, page_number,
                  x, y, signature_text):

    return add_text(
        file_path,
        output_path,
        page_number,
        x,
        y,
        signature_text,
        font_size=22
    )


def add_highlight(file_path, output_path, page_number,
                  x, y, width, height):

    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)

        rect = pymupdf.Rect(
            float(x),
            float(y),
            float(x) + float(width),
            float(y) + float(height)
        )

        annot = page.add_highlight_annot(rect)
        annot.update()

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


def add_rectangle(file_path, output_path, page_number,
                  x, y, width, height):

    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)

        rect = pymupdf.Rect(
            float(x),
            float(y),
            float(x) + float(width),
            float(y) + float(height)
        )

        annot = page.add_rect_annot(rect)
        annot.set_colors(stroke=(1, 0, 0))
        annot.update()

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


def add_drawing(file_path, output_path, page_number, points,
                color=(0, 0, 1), width=2):

    if len(points) < 2:
        raise ValueError("Drawing needs at least two points.")

    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)

        shape = page.new_shape()

        converted_points = [
            pymupdf.Point(float(point[0]), float(point[1]))
            for point in points
        ]

        shape.draw_polyline(converted_points)

        shape.finish(
            color=color,
            width=float(width)
        )

        shape.commit()

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


# --------------------------------------------------
# ANNOTATION MANAGEMENT
# --------------------------------------------------

def get_annotations(file_path, page_number):
    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)
        annotations = []

        annot = page.first_annot

        while annot:
            annotations.append({
                "xref": annot.xref,
                "type": annot.type[1],
                "content": annot.info.get("content", ""),
                "rect": [
                    annot.rect.x0,
                    annot.rect.y0,
                    annot.rect.x1,
                    annot.rect.y1
                ]
            })

            annot = annot.next

        return annotations

    finally:
        pdf.close()


def delete_annotation(file_path, output_path,
                      page_number, annotation_xref):

    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)

        found = False
        annot = page.first_annot

        while annot:
            if annot.xref == int(annotation_xref):
                page.delete_annot(annot)
                found = True
                break

            annot = annot.next

        if not found:
            raise ValueError("Annotation not found.")

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


# --------------------------------------------------
# PAGE MANAGEMENT
# --------------------------------------------------

def add_page(file_path, output_path, position=None,
             width=595, height=842):

    pdf = open_pdf(file_path)

    try:
        if position is None:
            pdf.new_page(
                width=float(width),
                height=float(height)
            )
        else:
            if position < 1 or position > len(pdf) + 1:
                raise ValueError("Invalid insertion position.")

            pdf.new_page(
                pno=position - 1,
                width=float(width),
                height=float(height)
            )

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


def rotate_page(file_path, output_path, page_number,
                rotation=90):

    if rotation not in (0, 90, 180, 270):
        raise ValueError("Rotation must be 0, 90, 180 or 270.")

    pdf = open_pdf(file_path)

    try:
        page = validate_page(pdf, page_number)

        page.set_rotation(rotation)

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


def delete_page(file_path, output_path, page_number):
    pdf = open_pdf(file_path)

    try:
        validate_page(pdf, page_number)

        if len(pdf) == 1:
            raise ValueError("A PDF must contain at least one page.")

        pdf.delete_page(page_number - 1)

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


def reorder_pages(file_path, output_path, page_order):
    pdf = open_pdf(file_path)

    try:
        expected = list(range(1, len(pdf) + 1))

        if sorted(page_order) != expected:
            raise ValueError(
                "Page order must contain every page number exactly once."
            )

        zero_based_order = [number - 1 for number in page_order]

        pdf.select(zero_based_order)

        return save_pdf(pdf, output_path)

    finally:
        pdf.close()


# --------------------------------------------------
# MERGE PDF FILES
# --------------------------------------------------

def merge_pdfs(file_paths, output_path):
    if not file_paths:
        raise ValueError("Provide at least one PDF file.")

    merged_pdf = pymupdf.open()

    try:
        for file_path in file_paths:
            source_pdf = open_pdf(file_path)

            try:
                merged_pdf.insert_pdf(source_pdf)
            finally:
                source_pdf.close()

        return save_pdf(merged_pdf, output_path)

    finally:
        merged_pdf.close()


# --------------------------------------------------
# SPLIT PDF FILES
# --------------------------------------------------

def split_pdf(file_path, output_directory):
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    pdf = open_pdf(file_path)
    output_files = []

    try:
        for page_index in range(len(pdf)):
            new_pdf = pymupdf.open()

            try:
                new_pdf.insert_pdf(
                    pdf,
                    from_page=page_index,
                    to_page=page_index
                )

                output_path = (
                    output_directory /
                    f"page_{page_index + 1}_{uuid4().hex[:8]}.pdf"
                )

                new_pdf.save(
                    str(output_path),
                    garbage=4,
                    deflate=True
                )

                output_files.append(str(output_path))

            finally:
                new_pdf.close()

        return output_files

    finally:
        pdf.close()
