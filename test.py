import cv2
import pyarrow.parquet as pq

clip = "data/Veo highlights ANUFC vs WEFC 23s/3 010545_-_Attack.mp4"
df = pq.read_table("outputs/3_010545_attack/detections.parquet").to_pandas()
print(df.describe()[["conf", "x1", "y1", "x2", "y2"]])
print("rows:", len(df), "frames:", df.frame_id.nunique())

cap = cv2.VideoCapture(clip)
ok, frame = cap.read(); cap.release()
for _, r in df[df.frame_id == 0].iterrows():
    cv2.rectangle(frame, (int(r.x1), int(r.y1)), (int(r.x2), int(r.y2)), (0, 255, 0), 2)
    cv2.putText(frame, f"{r.conf:.2f}", (int(r.x1), int(r.y1)-5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
cv2.imwrite("outputs/3_010545_attack/frame0_overlay.png", frame)
print("saved overlay -> outputs/3_010545_attack/frame0_overlay.png")