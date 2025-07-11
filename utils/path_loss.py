import numpy as np

def compute_path_loss_db(x, y, base_x, base_y, d0=1.0, n=2.0, shadowing_std_db=4.0):
    d = np.sqrt((x - base_x)**2 + (y - base_y)**2)
    d = max(d, 1e-3)  # prevent log(0)

    shadow_db = np.random.normal(0, shadowing_std_db)
    path_loss_db = 10 * n * np.log10(d / d0) + shadow_db

    # Clip path loss to a reasonable range to avoid absurd energy use
    path_loss_db = np.clip(path_loss_db, 30, 120)

    return path_loss_db
