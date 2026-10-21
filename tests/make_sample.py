"""Create a sample PDF and PNG with a coordinate table (used by the CI smoke test)."""
import sys

import pymupdf

out = sys.argv[1] if len(sys.argv) > 1 else "."
pts = [(351309.08, 351899.71), (351285.98, 351906.96), (351271.10, 351906.58), (351258.54, 351898.09),
       (351245.93, 351887.28), (351240.58, 351880.73)]
doc = pymupdf.open()
page = doc.new_page()
for i, (x, y) in enumerate(pts):
    yy = 100 + 16 * i
    page.insert_text((60, yy), str(i + 1), fontsize=10)
    page.insert_text((90, yy), f"{x:.2f}", fontsize=10)
    page.insert_text((180, yy), f"{y:.2f}", fontsize=10)
doc.save(f"{out}/sample.pdf")
page.get_pixmap(dpi=150).save(f"{out}/sample.png")
