with open('professional_trading_system.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with main() call
main_line_idx = None
for i, line in enumerate(lines):
    if 'main()' in line and 'if __name__' not in line:
        main_line_idx = i
        break

if main_line_idx is not None:
    # Keep only lines up to and including the main() call
    clean_lines = lines[:main_line_idx + 1]
    clean_lines.extend([
        '',
        "if __name__ == '__main__':",
        '    main()',
        ''
    ])
    
    with open('professional_trading_system.py', 'w', encoding='utf-8') as f:
        f.writelines(clean_lines)
    
    print('Archivo limpiado exitosamente')
    print(f'Líneas originales: {len(lines)}')
    print(f'Líneas después de limpieza: {len(clean_lines)}')
else:
    print('No se encontró la llamada a main()')