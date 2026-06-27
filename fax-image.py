from PIL import Image, ImageDraw, ImageFont

pages = [2, 4, 5, 7]
images = [Image.open(f"results/images/page_{p}.jpg") for p in pages]

# 全て同じサイズに揃える（最初の画像基準）
tw, th = images[0].size
resized = []
for img in images:
    if img.size != (tw, th):
        img = img.resize((tw, th), Image.LANCZOS)
    resized.append(img)

# 2x2 レイアウト
combined = Image.new("RGB", (tw * 2, th * 2), "white")
combined.paste(resized[0], (0, 0))
combined.paste(resized[1], (tw, 0))
combined.paste(resized[2], (0, th))
combined.paste(resized[3], (tw, th))

# 中央に赤字テキストを描画
text = "Pythonを使えば\nこんなFAXで来た書類も、\n一発で読み取って\n一覧表にできます"
draw = ImageDraw.Draw(combined)
font = ImageFont.truetype("/mnt/c/Windows/Fonts/meiryo.ttc", size=350)
bbox = draw.multiline_textbbox((0, 0), text, font=font)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]
x = (combined.width - text_w) // 2
y = (combined.height - text_h) // 2
padding = 40
draw.rectangle(
    [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
    fill="white",
)
draw.multiline_text((x, y), text, fill="red", font=font, align="left")

combined.save("results/images/fax-image.jpg", quality=95)
print(f"Saved: results/images/fax-image.jpg ({combined.size})")
