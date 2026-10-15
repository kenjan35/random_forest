from src.predict import predict
import numpy as np

prediction = predict("data/theft/Theft_1.csv")
indices = np.where(prediction == 1)[0]

print(indices)