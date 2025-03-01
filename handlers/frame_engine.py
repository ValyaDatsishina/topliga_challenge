import os
from io import BytesIO

from PIL import Image
import tempfile


def resize_by_width(image, new_width):
    width, height = image.size
    aspect_ratio = height / width
    new_height = int(new_width * aspect_ratio)
    resized_image = image.resize((new_width, new_height)).convert("RGBA")
    return resized_image


def resize_by_height(image, new_height):
    width, height = image.size
    aspect_ratio = width / height
    new_width = int(new_height * aspect_ratio)
    resized_image = image.resize((new_width, new_height)).convert("RGBA")
    return resized_image


def add_frame(photo, day):
    if day == 1:
        frame = Image.open('image/frame1.png').convert("RGBA")
    elif day == 2:
        frame = Image.open('image/frame2.png').convert("RGBA")
    else:
        frame = Image.open('image/frame3.png').convert("RGBA")

    width, height = frame.size

    image = photo

    if image.size[1] < height:
        image = resize_by_height(image, height)
        img_width, img_height = image.size
        left = (img_width - width) // 2
        top = (img_height - height) // 2
        right = left + width
        bottom = top + height
        image = image.crop((left, top, right, bottom))
    elif image.size[0] < width:
        image = resize_by_width(image, width)
        img_width, img_height = image.size
        left = (img_width - width) // 2
        top = (img_height - height) // 2
        right = left + width
        bottom = top + height
        image = image.crop((left, top, right, bottom))
    else:
        image = image.crop((0, 0, width, height)).convert("RGBA")

    image = Image.alpha_composite(image, frame)

    output_file_path = '/image/framed_image.png'  # Путь для сохранения файла
    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)  # Создаем директорию, если она не существует
    image.save(output_file_path, format='PNG')  # Сохраняем изображение

    return output_file_path
