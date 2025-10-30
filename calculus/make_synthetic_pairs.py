# make_synthetic_pairs.py
import cv2, numpy as np, os, json

os.makedirs("data", exist_ok=True)

# Imagen base: rectángulos y círculos para dar features
base = np.zeros((480, 640), np.uint8)
cv2.rectangle(base, (80, 60), (560, 420), 200, 3)
for i in range(6):
    cv2.circle(base, (120+i*80, 120), 18, 255, -1)
for i in range(5):
    cv2.circle(base, (140+i*90, 360), 14, 180, -1)
cv2.putText(base, "TEST FM", (210,260), cv2.FONT_HERSHEY_SIMPLEX, 1.8, 220, 3, cv2.LINE_AA)

# Definimos una homografia suave (rotacion + escala + traslacion + ligera perspectiva)
H_true = np.array([[ 0.96, -0.04,  30.0],
                   [ 0.05,  0.98,  22.0],
                   [ 1e-4, -1e-4,  1.0 ]], dtype=np.float32)

warped = cv2.warpPerspective(base, H_true, (640, 480))

cv2.imwrite("data/A1.png", base)
cv2.imwrite("data/B1.png", warped)

# Un segundo par: escala distinta + ruido leve
H2 = np.array([[ 1.02,  0.02, -20.0],
               [-0.03,  0.97,  15.0],
               [ 8e-5,  6e-5,   1.0 ]], dtype=np.float32)
warped2 = cv2.warpPerspective(base, H2, (640, 480))
noise = (np.random.randn(*warped2.shape) * 3).astype(np.int16)
warped2 = np.clip(warped2.astype(np.int16) + noise, 0, 255).astype(np.uint8)

cv2.imwrite("data/A2.png", base)
cv2.imwrite("data/B2.png", warped2)

# Pairs.txt
with open("pairs.txt", "w", encoding="utf-8") as f:
    f.write("data/A1.png; data/B1.png\n")
    f.write("data/A2.png; data/B2.png\n")

print("Listo. Archivos escritos en ./data y ./pairs.txt")
