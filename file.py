import face_recognition

image = face_recognition.load_image_file("Hamza.jpg")
encodings = face_recognition.face_encodings(image)

if encodings:
    print("Visage détecté")
else:
    print("Aucun visage")
