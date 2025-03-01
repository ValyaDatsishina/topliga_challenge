import os
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
import logging

class ImageProcessor:
    """Класс для обработки изображений и добавления рамок"""
    
    FRAME_PATHS = {
        1: 'image/frame1.png',
        2: 'image/frame2.png',
        3: 'image/frame3.png'
    }
    OUTPUT_DIR = 'image'
    OUTPUT_FILE = 'framed_image.png'
    
    @staticmethod
    def resize_image(
        image: Image.Image,
        target_size: Tuple[int, int],
        resize_by: str = 'width'
    ) -> Image.Image:
        """
        Изменяет размер изображения с сохранением пропорций
        
        Args:
            image: Исходное изображение
            target_size: Целевой размер (ширина, высота)
            resize_by: Метод изменения размера ('width' или 'height')
            
        Returns:
            Измененное изображение
        """
        width, height = image.size
        target_width, target_height = target_size
        
        if resize_by == 'width':
            aspect_ratio = height / width
            new_height = int(target_width * aspect_ratio)
            new_size = (target_width, new_height)
        else:
            aspect_ratio = width / height
            new_width = int(target_height * aspect_ratio)
            new_size = (new_width, target_height)
            
        return image.resize(new_size).convert("RGBA")
    
    @staticmethod
    def crop_to_size(
        image: Image.Image,
        target_size: Tuple[int, int]
    ) -> Image.Image:
        """
        Обрезает изображение до нужного размера по центру
        
        Args:
            image: Исходное изображение
            target_size: Целевой размер (ширина, высота)
            
        Returns:
            Обрезанное изображение
        """
        img_width, img_height = image.size
        target_width, target_height = target_size
        
        left = (img_width - target_width) // 2
        top = (img_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        
        return image.crop((left, top, right, bottom))
    
    @classmethod
    def add_frame(
        cls,
        photo: Image.Image,
        day: int
    ) -> Optional[str]:
        """
        Добавляет рамку к фотографии
        
        Args:
            photo: Исходное изображение
            day: Номер дня (1-3)
            
        Returns:
            Путь к сохраненному файлу или None в случае ошибки
        """
        try:
            if day not in cls.FRAME_PATHS:
                raise ValueError(f"Неверный номер дня: {day}")
            
            frame_path = cls.FRAME_PATHS[day]
            if not os.path.exists(frame_path):
                raise FileNotFoundError(f"Файл рамки не найден: {frame_path}")
            
            frame = Image.open(frame_path).convert("RGBA")
            frame_size = frame.size
            
            # Изменяем размер и обрезаем изображение
            if photo.size[1] < frame_size[1]:
                photo = cls.resize_image(photo, frame_size, 'height')
            elif photo.size[0] < frame_size[0]:
                photo = cls.resize_image(photo, frame_size, 'width')
            
            photo = cls.crop_to_size(photo, frame_size)
            
            # Накладываем рамку
            result = Image.alpha_composite(photo, frame)
            
            # Создаем директорию для сохранения, если её нет
            output_dir = Path(cls.OUTPUT_DIR)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем результат
            output_path = output_dir / cls.OUTPUT_FILE
            result.save(output_path, format='PNG')
            
            return str(output_path)
            
        except Exception as e:
            logging.error(f"Ошибка при обработке изображения: {e}")
            return None

# Для обратной совместимости
def add_frame(photo: Image.Image, day: int) -> Optional[str]:
    """
    Обертка для обратной совместимости
    """
    return ImageProcessor.add_frame(photo, day)
