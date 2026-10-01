import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

# 1. Verilerimizi Yükleme ve Temizleme
print("Veri seti işleniyor...")
df = pd.read_csv('healthcare-dataset-stroke-data.csv')
df = df.drop('id', axis=1)

# Eksik verileri doldur
imputer = SimpleImputer(strategy='mean')
df['bmi'] = imputer.fit_transform(df[['bmi']])

# Kategorik verileri sayıya çevirme
categorical_cols = ['gender', 'ever_married', 'work_type', 'Residence_type', 'smoking_status']
encoders = {}
for col in categorical_cols:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    encoders[col] = le

# 2. Veriyi Bölme kısmı
X = df.drop('heart_attack', axis=1)
y = df['heart_attack']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Ölçeklendirme kısmı
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# 4. GridSearch ile En İyi Modeli Bulmak için
print("En iyi model parametreleri aranıyor...")

# SMOTE kullanmadan veri dengesizliğini çözen kısım
rf = RandomForestClassifier(random_state=42, class_weight='balanced')

param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [None, 10, 20],
    'min_samples_split': [2, 5]
}

grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, cv=3, n_jobs=-1, verbose=1)
grid_search.fit(X_train, y_train)

best_model = grid_search.best_estimator_
print(f"En iyi parametreler: {grid_search.best_params_}")

# 5. Raporlamak için 
y_pred = best_model.predict(X_test)
print("\nModel Performans Raporu:")
print(classification_report(y_test, y_pred))

# 6. verileri kaydetme 
with open('model/model.pkl', 'wb') as f:
    pickle.dump(best_model, f)

with open('model/scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

with open('model/encoders.pkl', 'wb') as f:
    pickle.dump(encoders, f)

print("Model başarıyla kaydedildi! (Ekstra kütüphane gerekmedi)")