import pandas as pd, numpy as np
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

df = pd.read_csv('../data/bhubaneswar/grid_features.csv')

# GEOGRAPHIC SPLIT: west half trains, east half tests
split_lon = df.lon.median()
train = df[df.lon <= split_lon]
test  = df[df.lon >  split_lon]

print('Train cells: %d   Test cells: %d' % (len(train), len(test)))

FEATURES = ['tree_frac', 'grass_frac', 'built_frac',
            'water_frac', 'bare_frac', 'ndvi_mean']
TARGET = 'lst_mean'

model = XGBRegressor(n_estimators=300, max_depth=5,
                      learning_rate=0.05, random_state=42)
model.fit(train[FEATURES], train[TARGET])

pred = model.predict(test[FEATURES])
print('RMSE  %.2f C' % np.sqrt(mean_squared_error(test[TARGET], pred)))
print('MAE   %.2f C' % mean_absolute_error(test[TARGET], pred))
print('R2    %.3f'   % r2_score(test[TARGET], pred))

for name, imp in sorted(zip(FEATURES, model.feature_importances_),
                         key=lambda x: -x[1]):
    print('  %-12s %.3f' % (name, imp))