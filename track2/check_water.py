import pandas as pd
df = pd.read_csv('../data/bhubaneswar/grid_features.csv')

# without water cells
no_water = df[df.water_frac < 0.1]
print('Without water, n=', len(no_water))
print(no_water[['tree_frac','built_frac','lst_mean']].corr()['lst_mean'])