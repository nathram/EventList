import sqlite3
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

def load_labeled_data():
    conn = sqlite3.connect("emails_labeled.db")
    df = pd.read_sql_query("SELECT subject, body, is_event FROM emails WHERE is_event IS NOT NULL", conn)
    conn.close()
    return df

# Load and prepare data
df = load_labeled_data()
X = df['subject'] + " " + df['body']
y = df['is_event']

# Split into train/test
X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y)

# Create model pipeline with class_weight balanced
model = make_pipeline(
    TfidfVectorizer(),
    LogisticRegression(class_weight='balanced', max_iter=1000)
)

# Train and evaluate
model.fit(X_train, y_train)
print(classification_report(y_test, model.predict(X_test)))

'''
Accuracy:
 precision    recall  f1-score   support

           0       0.98      0.96      0.97        54
           1       0.87      0.93      0.90        14

    accuracy                           0.96        68
   macro avg       0.92      0.95      0.93        68
weighted avg       0.96      0.96      0.96        68
'''

# Save model
joblib.dump(model, "event_classifier.pkl")
print("Model saved as 'event_classifier.pkl'")