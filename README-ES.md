<p align="right">
  <a href="./README.md">Português</a> |
  <a href="./README-EN.md">English</a> |
  <strong>Español</strong>
</p>

# Firmware de carátulas para EverDrive-MD V2

Firmware modificada para EverDrive-MD V2 que añade **carátulas de juegos directamente en el explorador de archivos**, haciendo que la navegación por la tarjeta SD sea más atractiva, práctica y similar a los menús modernos de flashcarts.

El proyecto incluye el firmware con soporte para carátulas y una herramienta para Windows capaz de convertir imágenes PNG/JPG en archivos `.PAK`, utilizados por el EverDrive para mostrar automáticamente la carátula correspondiente al juego seleccionado.

Este trabajo fue realizado sin acceso al código fuente original del sistema operativo del EverDrive-MD. El firmware final es el resultado de ingeniería inversa.

<h2 align="center">🎥 Demostración en vídeo</h2>

<p align="center">
  <a href="https://www.youtube.com/watch?v=ZBZwvmXG3as&t=1s">
    <img
      src="https://i.imgur.com/IX8iTHN.jpeg"
      alt="Ver la demostración en vídeo"
      width="700"
    >
  </a>
</p>

<p align="center">
  Haz clic en la imagen para verlo en YouTube.
</p>

# Créditos

Firmware de carátulas y herramienta por: Tavinho Games

Sígueme en Instagram: **[@tavinho.games](https://instagram.com/tavinho.games)**  
Suscríbete al canal: **[youtube.com/@tavinho-games](https://youtube.com/@tavinho-games)**

## Límite de carátulas

En la versión actual del firmware, cada archivo `.PAK` admite hasta **150 carátulas**.

Los paquetes se separan según la primera letra o número del nombre de la ROM:

- `0.PAK` para juegos cuyos nombres comienzan con un número.
- `A.PAK` hasta `Z.PAK` para juegos cuyos nombres comienzan con una letra.

Esto permite hasta **4050 carátulas en total**.

# Funciones implementadas

- Visualización automática de carátulas al navegar por ROMs `.bin`.
- Carátulas de 128x160 píxeles, equivalentes a 16x20 tiles de Mega Drive.
- Herramienta externa para convertir carátulas PNG/JPG y crear los archivos `.PAK`.
- Editor visual de recorte y encuadre.
- Variantes PT-BR y ES.
- Corrección del cambio de página en el explorador de archivos: al avanzar o retroceder una página, el cursor vuelve al primer elemento de la página.

## Cómo usarlo

1. Copia el archivo de firmware `.BIN` en la tarjeta SD.
2. En el EverDrive-MD, abre el menú **OS Update**, selecciona el archivo y actualiza utilizando el firmware modificado.
3. En el ordenador, abre la herramienta **EDMD Cover Pack Tool**.
4. Selecciona la carpeta donde se encuentran las ROMs.
5. Selecciona la carpeta donde se encuentran las carátulas.
6. Elige la raíz de la tarjeta SD como destino.
7. Haz clic en **Generar .PAK**.
8. Comprueba que los archivos `0.PAK`, `A.PAK` hasta `Z.PAK` se hayan generado en la raíz de la tarjeta SD.
9. Inserta la tarjeta SD en el EverDrive-MD y abre el explorador de archivos.
10. Al colocar el cursor sobre una ROM con una carátula asociada, la carátula se mostrará automáticamente.

## Base técnica

Base utilizada durante el desarrollo:

- OS v36 para EverDrive-MD V2.x.
- Imagen principal de 64 KiB extraída del banco principal: `M29W640-extract-os_bank_10000.bin`.
- Base de ejecución aparente: `0xFF0000`.
- Área de código inyectado utilizada: a partir de `0x9C00`.
- Límite empírico de seguridad: mantener el final del código por debajo de `0xA800`.

Regla principal de seguridad:

- El área inicial de la memoria flash y el sistema de recuperación nunca deben modificarse.
- El desarrollo siempre se realizó sobre el banco principal del sistema operativo.
- El recovery/sistema operativo de reserva del clon se conservó para permitir la restauración manteniendo pulsados `A+B+C` al encender la consola.

## Lenguajes y herramientas utilizados

Lenguajes:

- Python 3: generadores de firmware, conversores de imágenes, creador de `.PAK`, interfaz gráfica y scripts de validación.
- Assembly Motorola 68000: código inyectado en el firmware, generado como bytes mediante scripts de Python.
- Tkinter: interfaz gráfica de la herramienta de carátulas.
- PowerShell: automatización local, copia a la tarjeta SD y verificaciones.

Bibliotecas/herramientas:

- Pillow: lectura, recorte, redimensionamiento, cuantización y vista previa de imágenes.
- Capstone: desensamblado y validación de fragmentos de código 68000.
- PyInstaller: empaquetado de la herramienta como archivo `.exe`.
- Hash SHA-256: validación de archivos locales y copiados a la tarjeta SD.

## Ingeniería inversa utilizada

El proceso comenzó con el sistema operativo v36 en formato binario, sin código fuente. La ingeniería inversa se realizó mediante:

- búsqueda de cadenas ASCII para localizar menús, mensajes y rutinas;
- desensamblado 68000 en big-endian;
- identificación de tablas de punteros de texto;
- identificación de rutinas FAT/SD ya existentes en el sistema operativo;
- identificación de rutinas de texto, pantalla y VDP;
- pruebas incrementales en hardware real;
- validación visual;
- comparación byte a byte entre POCs estables y nuevas POCs.

Offsets importantes:

- `0x65E2`: hook utilizado después del repintado del explorador de archivos.
- `0x6934` y `0x69A8`: ajustes para que el cursor vuelva a la parte superior al cambiar de página.
- `0x7606`: llamada que dibujaba el logotipo grande `GAMEJOY84` en la pantalla About; sustituida por NOPs conservando la limpieza de la pila.
- `0x9C00`: inicio del código inyectado.
- `0xA800`: límite empírico de seguridad para evitar problemas de arranque en el clon.
- `0xFFCC64`: bloque de estado FAT/explorador guardado y restaurado.
- `0xFFCC7C`: puntero del búfer/cabecera del directorio guardado y restaurado.

## Cómo funciona el firmware

El explorador de archivos original continúa siendo dibujado por el sistema operativo. Después de que el explorador vuelve a dibujar la lista, el hook llama al código inyectado:

1. Guarda los registros del 68000.
2. Guarda el estado interno de FAT/explorador.
3. Comprueba si el elemento seleccionado parece ser una ROM `.BIN`.
4. Decide qué archivo `.PAK` abrir según el primer carácter del nombre de la ROM:
   - los números utilizan `0.PAK`;
   - `A` utiliza `A.PAK`;
   - `B` utiliza `B.PAK`;
   - y así sucesivamente hasta `Z.PAK`.
5. Busca la carátula mediante el nombre normalizado dentro del catálogo `SCP2`.
6. Si la encuentra, lee la imagen `.SCIMG` ya convertida.
7. Copia la paleta y los tiles al VDP y dibuja la carátula en el lado derecho del explorador.
8. Si no encuentra ninguna carátula, limpia el área destinada a la carátula.
9. Restaura el estado FAT/explorador y los registros.
10. Vuelve al flujo original del sistema operativo.

El firmware no decodifica archivos PNG/JPG. Toda la conversión pesada se realiza en el ordenador mediante la herramienta externa.

## Formato de las carátulas

Formato final mostrado en la consola:

- resolución: 128x160 píxeles;
- tiles: 16x20;
- colores: 16 colores en una paleta de Genesis;
- tiles 4bpp en el formato del VDP de Mega Drive;
- archivo intermedio: `.SCIMG`;
- paquete final en la tarjeta SD: `.PAK` con catálogo `SCP2`.

Los archivos `.PAK` se almacenan en la raíz de la tarjeta SD:

```text
0.PAK
A.PAK
B.PAK
...
Z.PAK
```

Para añadir o corregir carátulas, solo es necesario generar nuevamente los archivos `.PAK`. No es necesario actualizar el firmware.

## Herramienta de carátulas

Archivo principal:

- `EDMD-Cover-Pack-Tool.exe`

Código fuente:

- `tools/edmd_cover_pack_gui.py`

Funciones:

- selecciona la carpeta de ROMs;
- selecciona la carpeta de carátulas;
- asocia carátulas mediante el nombre relativo o un nombre idéntico;
- permite utilizar un archivo CSV manual para asociaciones específicas;
- incluye un editor de recorte de 128x160;
- genera vistas previas en el ordenador;
- genera archivos `.PAK` por letra;
- incluye interfaz en portugués, inglés y español;
- incluye créditos y enlaces.

## Resultado final

La POC final validada fue la familia POC135:

- carátulas automáticas funcionando;
- navegación del explorador funcionando;
- regreso mediante `B` funcionando;
- cambio de páginas ajustado;
- acceso a `OS UPDATE` funcionando incluso después de utilizar el explorador;
- pantalla About personalizada funcionando;
- texto de Instagram legible;
- variantes PT-BR y ES funcionando.

Consulta también:

- `POC-REVISOES-E-TESTES.md`
- `NOTAS-TECNICAS-FIRMWARE.md`
