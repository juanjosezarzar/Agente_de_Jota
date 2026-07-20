#!/usr/bin/env python3
import os
import sys
import subprocess
import markdown

def convert_md_to_pdf(md_path):
    if not os.path.exists(md_path):
        print(f"Error: El archivo {md_path} no existe.")
        return False
        
    print(f"Procesando {md_path}...")
    
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
        
    # Extraer metadatos y limpiar el markdown
    meta_labels = ["Para", "De", "Período de Análisis", "Tono de la Cuenta"]
    meta_data = {}
    clean_lines = []
    
    title = "@gravitymallsport"
    subtitle = "Reporte de Rendimiento Instagram"
    has_title = False
    has_subtitle = False
    
    for line in md_content.split("\n"):
        # Extraer título principal
        if line.startswith("# ") and not has_title:
            title = line[2:].strip()
            has_title = True
            continue
        # Extraer subtítulo
        if line.startswith("## ") and not has_subtitle and ("¡Escalando" in line or "Algoritmo" in line or "Comunidad" in line):
            subtitle = line[3:].replace("*", "").strip()
            has_subtitle = True
            continue
            
        # Extraer metadatos
        found_meta = False
        for label in meta_labels:
            if f"**{label}:**" in line:
                val = line.split(f"**{label}:**", 1)[1].strip()
                meta_data[label] = val
                found_meta = True
                break
        
        if not found_meta:
            clean_lines.append(line)
            
    # Reconstruir el markdown limpio
    clean_md = "\n".join(clean_lines)
    
    # Convertir a HTML
    html_body = markdown.markdown(clean_md, extensions=['tables', 'fenced_code'])
    
    # Crear HTML completo con estilo corporativo de Gravity
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte de Rendimiento - Gravity Mall Sport</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #7b2cbf;
            --primary-light: #f3e8ff;
            --primary-dark: #5a189a;
            --text-color: #2d3748;
            --bg-light: #f7fafc;
            --border-color: #e2e8f0;
            --success: #38a169;
            --purple-gradient: linear-gradient(135deg, #7b2cbf 0%, #5a189a 100%);
        }}
        
        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            color: var(--text-color);
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background-color: #ffffff;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        
        .container {{
            max-width: 850px;
            margin: 0 auto;
            padding: 50px 40px;
        }}
        
        /* Encabezado del Reporte */
        .report-header {{
            border-bottom: 4px solid var(--primary);
            padding-bottom: 25px;
            margin-bottom: 35px;
        }}
        
        .report-header h1 {{
            font-family: 'Outfit', sans-serif;
            color: var(--primary-dark);
            font-size: 2.3rem;
            margin: 0 0 8px 0;
            font-weight: 800;
            letter-spacing: -0.5px;
        }}
        
        .report-header h2 {{
            font-family: 'Outfit', sans-serif;
            color: #4a5568;
            font-size: 1.2rem;
            margin: 0;
            font-weight: 400;
            font-style: italic;
        }}
        
        /* Caja de Metadatos */
        .meta-info {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px 25px;
            background: linear-gradient(to right, #fbf8ff, #ffffff);
            padding: 20px 25px;
            border-radius: 10px;
            border-left: 5px solid var(--primary);
            border-top: 1px solid var(--border-color);
            border-right: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 40px;
            font-size: 0.95rem;
        }}
        
        .meta-item {{
            display: flex;
            align-items: baseline;
        }}
        
        .meta-label {{
            font-weight: 700;
            color: var(--primary-dark);
            width: 150px;
            flex-shrink: 0;
        }}
        
        .meta-val {{
            color: #4a5568;
        }}
        
        /* Tipografía de Secciones */
        h2 {{
            font-family: 'Outfit', sans-serif;
            color: var(--primary-dark);
            font-size: 1.5rem;
            margin-top: 40px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
            font-weight: 700;
            page-break-before: always;
        }}
        
        /* Evitar salto de página en la primera sección */
        h2:first-of-type {{
            page-break-before: avoid;
            margin-top: 0;
        }}
        
        h3 {{
            font-family: 'Outfit', sans-serif;
            color: #2d3748;
            font-size: 1.15rem;
            margin-top: 25px;
            margin-bottom: 15px;
            font-weight: 600;
            border-left: 3px solid var(--primary);
            padding-left: 10px;
        }}
        
        p {{
            margin-top: 0;
            margin-bottom: 18px;
            font-size: 1rem;
            color: #4a5568;
            text-align: justify;
        }}
        
        /* Listas */
        ul, ol {{
            margin-top: 0;
            margin-bottom: 22px;
            padding-left: 24px;
        }}
        
        li {{
            margin-bottom: 10px;
            font-size: 1rem;
            color: #4a5568;
        }}
        
        strong {{
            color: #2d3748;
            font-weight: 600;
        }}
        
        /* Tablas */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 30px 0;
            font-size: 0.95rem;
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }}
        
        th {{
            background-color: var(--primary);
            color: white;
            text-align: left;
            font-weight: 600;
            padding: 14px 18px;
            font-family: 'Outfit', sans-serif;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 14px 18px;
            border-bottom: 1px solid var(--border-color);
            color: #4a5568;
        }}
        
        tr:nth-child(even) {{
            background-color: var(--bg-light);
        }}
        
        /* Destacados / Citas */
        blockquote {{
            margin: 30px 0;
            padding: 22px 28px;
            background-color: var(--primary-light);
            border-left: 6px solid var(--primary);
            border-radius: 6px;
        }}
        
        blockquote p {{
            margin: 0;
            color: var(--primary-dark);
            font-size: 1.05rem;
            font-weight: 500;
            font-family: 'Outfit', sans-serif;
            font-style: italic;
        }}
        
        /* Separadores */
        hr {{
            border: 0;
            height: 1px;
            background: var(--border-color);
            margin: 45px 0;
        }}
        
        /* Ajustes de Impresión */
        @media print {{
            body {{
                font-size: 10.5pt;
            }}
            .container {{
                padding: 0;
                max-width: 100%;
            }}
            h2, h3, table, blockquote {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Encabezado Estilizado -->
        <div class="report-header">
            <h1>{title}</h1>
            <h2>{subtitle}</h2>
        </div>
        
        <!-- Metadatos Estilizados -->
        <div class="meta-info">
            <div class="meta-item">
                <span class="meta-label">Para:</span>
                <span class="meta-val">{meta_data.get('Para', 'Equipo Directivo y Staff')}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">De:</span>
                <span class="meta-val">{meta_data.get('De', 'Agente de IA y Marketing')}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Período de Análisis:</span>
                <span class="meta-val">{meta_data.get('Período de Análisis', 'Semanal')}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Tono de la Cuenta:</span>
                <span class="meta-val">{meta_data.get('Tono de la Cuenta', 'Comunitario y Motivador')}</span>
            </div>
        </div>
        
        <!-- Cuerpo del Reporte -->
        {html_body}
    </div>
</body>
</html>
"""
    
    # Escribir HTML intermedio
    html_path = md_path.replace(".md", ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML generado: {html_path}")
    
    # Ruta del PDF final
    pdf_path = md_path.replace(".md", ".pdf")
    
    # Ejecutar Google Chrome en modo headless
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    chrome_cmd = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        f"--print-to-pdf={pdf_path}",
        html_path
    ]
    
    try:
        subprocess.run(chrome_cmd, check=True)
        print(f"¡PDF generado con éxito en: {pdf_path}!")
        return pdf_path
    except Exception as e:
        print(f"Error al compilar PDF usando Chrome: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        md_file = sys.argv[1]
    else:
        # Buscar el reporte más reciente
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reportes")
        md_files = [os.path.join(reports_dir, f) for f in os.listdir(reports_dir) if f.endswith(".md")]
        if not md_files:
            print("No se encontraron reportes .md en la carpeta reportes.")
            sys.exit(1)
        md_files.sort()
        md_file = md_files[-1]
        
    convert_md_to_pdf(md_file)
