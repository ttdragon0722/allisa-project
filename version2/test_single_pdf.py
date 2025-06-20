from os.path import isfile
from lib.SinglePDF import SinglePDF
from lib.PDFViewer import PDFViewer

if __name__ == "__main__":
    paths = [
        "C:/Users/Rex/Downloads/alisa project/source/ADN253_RA1-B.pdf",
        "C:/Users/Rex/Downloads/alisa project/source/ADN253_RA1-T.pdf",
        "C:/Users/Rex/Downloads/alisa project/source/PR810_MB_RA-PDF-201123B.pdf",
        "C:/Users/Rex/Downloads/alisa project/source/PR810_MB_RA-PDF-201123T.pdf",
        "C:/Users/Rex/Downloads/alisa project/source/X103-NP18A-1212_RA-PDF-250204B.pdf",
        "C:/Users/Rex/Downloads/alisa project/source/X103-NP18A-1212_RA-PDF-250204T.pdf",
        "C:/Users/Rex/Downloads/alisa project/source/X103-PE30-48_RA-B.pdf",
        "C:/Users/Rex/Downloads/alisa project/source/X103-PE30-48_RA-T.pdf"
    ]

    for i, path in enumerate(paths):
        print(f"\n--- [{i+1}/{len(paths)}] 測試 PDF: {path} ---")
        
        
        if not isfile(path):
            print("❌ 找不到檔案，略過")
            continue

        pdf = SinglePDF(path=path)

        
        if not pdf.doc:
            print("❌ PDF 無法載入，略過")
            continue

        try:
            bbox = pdf.get_trimmed_bounding_box_v6(idx=0)
            print(f"✅ BoundingBox: ({bbox.x0}, {bbox.y0}) - ({bbox.x1}, {bbox.y1})")
        except Exception as e:
            print(f"⚠️ 發生錯誤：{e}")
