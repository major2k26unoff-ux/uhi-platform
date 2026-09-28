import numpy as np, os
import matplotlib.pyplot as plt

os.makedirs('stub_data/bhubaneswar/preview', exist_ok=True)

size = 400
y, x = np.mgrid[0:size, 0:size]
heat = (np.exp(-((x - 200)**2 + (y - 180)**2) / 9000) * 12
        + np.random.normal(0, 0.4, (size, size)) + 30)

for name, cmap, vmin, vmax in [
    ('lst', 'inferno', 25, 45),
    ('ndvi', 'RdYlGn', -0.2, 0.8),
    ('landcover', 'tab10', 0, 8),
    ('rgb', 'viridis', 0, 1),
    ('priority', 'YlOrRd', 0, 1),
]:
    plt.figure(figsize=(6, 6))
    data = heat if name == 'lst' else np.random.rand(size, size) * (vmax - vmin) + vmin
    plt.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax)
    plt.axis('off')
    plt.savefig(f'stub_data/bhubaneswar/preview/{name}.png',
                bbox_inches='tight', pad_inches=0, dpi=100, transparent=True)
    plt.close()
    print('Wrote', name)