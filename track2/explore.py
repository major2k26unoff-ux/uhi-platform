import pandas as pd, matplotlib.pyplot as plt

df = pd.read_csv('../data/bhubaneswar/grid_features.csv')

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

axes[0].scatter(df.tree_frac, df.lst_mean, s=3, alpha=0.25)
axes[0].set_xlabel('Fraction of cell covered by trees')
axes[0].set_ylabel('Mean ground temperature (C)')
axes[0].set_title('Trees vs temperature')

axes[1].scatter(df.built_frac, df.lst_mean, s=3, alpha=0.25, color='firebrick')
axes[1].set_xlabel('Fraction of cell that is built-up')
axes[1].set_ylabel('Mean ground temperature (C)')
axes[1].set_title('Built-up vs temperature')

plt.tight_layout()
plt.savefig('../data/bhubaneswar/exploration.png', dpi=150)

print(df[['tree_frac', 'built_frac', 'ndvi_mean', 'lst_mean']].corr()['lst_mean'])