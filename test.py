import fitz  # PyMuPDF

def search_text_in_pdf(pdf_path, keyword):
    doc = fitz.open(pdf_path)
    keyword = keyword.lower()  # 轉成小寫方便比對

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text('blocks')
        
        for b in blocks:
            x0, y0, x1, y1, text, block_no, block_type = b
            text_clean = text.strip()
            if keyword in text_clean.lower():
                print(f'頁面 {page_num+1}：文字 "{text_clean}" 出現在坐標 ({x0:.2f}, {y0:.2f}) ~ ({x1:.2f}, {y1:.2f})')

if __name__ == '__main__':
    pdf_file = 'sample.pdf'
    search_word = input("請輸入要搜尋的文字：")
    search_text_in_pdf(pdf_file, search_word)
