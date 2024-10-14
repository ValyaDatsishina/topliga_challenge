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


def add_frame(photo):
    frame = Image.open('image/frame.png').convert("RGBA")
    width, height = frame.size
    image = photo

    if image.size[0] < width:
        image = resize_by_width(image, width)
        img_width, img_height = image.size
        left = (img_width - width) // 2
        top = (img_height - height) // 2
        right = left + width
        bottom = top + height
        image = image.crop((left, top, right, bottom))

    elif image.size[1] < height:
        image = resize_by_height(image, height)
        img_width, img_height = image.size
        left = (img_width - width) // 2
        top = (img_height - height) // 2
        right = left + width
        bottom = top + height
        image = image.crop((left, top, right, bottom))
    else:
        image = image.crop((0, 0, width, height)).convert("RGBA")

    image = Image.alpha_composite(image, frame)

    # Сохраняем результат в BytesIO
    output = BytesIO()
    image.save(output, format='PNG')
    output.seek(0)  # Сбрасываем указатель на начало
    print(type(output))

    return output
    # image = Image.alpha_composite(image, frame)
    # tmp_file = 'image/framed_image.png'
    # image.save(tmp_file)
    #
    # return tmp_file
