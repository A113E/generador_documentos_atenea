from PIL import Image
import os

def create_favicon():
    """Convierte el logo en un favicon.ico"""
    
    # Ruta de tu logo
    logo_path = 'static/img/logo.png'
    
    # Verificar que el logo existe
    if not os.path.exists(logo_path):
        print(f'❌ Error: No se encontró el logo en {logo_path}')
        return False
    
    try:
        # Abrir la imagen
        img = Image.open(logo_path)
        
        # Convertir a RGB si es necesario (para PNG con transparencia)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Crear fondo blanco
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            # Pegar la imagen sobre fondo blanco
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Redimensionar a 32x32 para favicon estándar
        img = img.resize((32, 32), Image.Resampling.LANCZOS)
        
        # Guardar como ICO
        favicon_path = 'static/img/favicon.ico'
        img.save(favicon_path, format='ICO')
        
        print(f'✅ Favicon creado exitosamente en: {favicon_path}')
        
        # También crear versiones adicionales para mejor compatibilidad
        # Versión 16x16
        img_16 = img.resize((16, 16), Image.Resampling.LANCZOS)
        img_16.save('static/img/favicon-16x16.png', format='PNG')
        
        # Versión 32x32
        img.save('static/img/favicon-32x32.png', format='PNG')
        
        # Versión 180x180 para Apple
        img_180 = Image.open(logo_path)
        if img_180.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img_180.size, (255, 255, 255))
            background.paste(img_180, mask=img_180.split()[-1] if img_180.mode == 'RGBA' else None)
            img_180 = background
        img_180 = img_180.resize((180, 180), Image.Resampling.LANCZOS)
        img_180.save('static/img/apple-touch-icon.png', format='PNG')
        
        print('✅ Versiones adicionales creadas:')
        print('   - favicon-16x16.png')
        print('   - favicon-32x32.png')
        print('   - apple-touch-icon.png')
        
        return True
        
    except Exception as e:
        print(f'❌ Error al crear favicon: {e}')
        return False

if __name__ == '__main__':
    create_favicon()