from reportlab.pdfgen import canvas
c = canvas.Canvas('test_hello.pdf')
c.drawString(100, 750, 'Hello, this is a test page.')
c.drawString(100, 700, 'This is the second line.')
c.showPage()
c.drawString(100, 750, 'This is page two of the test.')
c.showPage()
c.save()
print('Created test_hello.pdf')
import os
print(f'Size: {os.path.getsize("test_hello.pdf")} bytes')
