import pandas as pd
from PIL import Image
import os
import numpy as np
import cv2

import torch
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split

def load_metadata(path):
    """ Carga los metadatos de un CSV. """
    return pd.read_csv(path)


# Definir función para cargar y procesar una imagen
def load_and_process_image(image_path, target_size=(28, 28)):
    # Cargar imagen
    image = Image.open(image_path)
    # Convertir a espacio de color HSV
    image_hsv = image.convert('HSV')
    # Redimensionar imagen
    image_resized = image_hsv.resize(target_size)
    # Convertir a array de numpy
    image_array = np.array(image_resized)

    return image_array


def process_annotated_images(annotated_patches_df, annotated_images_dir):
    """ Procesa las imágenes anotadas basándose en los metadatos proporcionados. """
    patches_data = []
    for index, row in annotated_patches_df.iterrows():
        # Divide el patch_id en las partes necesarias
        patch_id_parts = row['ID'].split('.')
        image_folder = patch_id_parts[0]
        image_file = patch_id_parts[1] + '.png'

        # Construye la ruta de la carpeta y el archivo de la imagen
        image_folder_path = os.path.join(annotated_images_dir, image_folder)
        image_path = os.path.join(image_folder_path, image_file)

        # Verifica si la ruta del archivo existe antes de procesar
        if os.path.exists(image_path):
            image_array = load_and_process_image(image_path)
            patches_data.append((image_array, row['Presence']))
        else:
            print(f"No se encontró la imagen: {image_path}")
            
    return patches_data


def prepare_dataset(patches_data):
    """ Prepara el conjunto de datos para el entrenamiento. """
    patches_data_array = np.array([i[0] for i in patches_data])
    patches_labels_array = np.array([i[1] for i in patches_data])
    return patches_data_array, patches_labels_array


def convert_to_tensors(patches_data_array, patches_labels_array):
    """ Convertir arrays de Numpy a tensores de PyTorch. """
    patches_data_array = patches_data_array.transpose((0, 3, 1, 2))
    data_tensor = torch.tensor(patches_data_array, dtype=torch.float32)
    labels_tensor = torch.tensor(patches_labels_array, dtype=torch.float32)
    return data_tensor, labels_tensor

def normalize_tensors(data_tensor):
    """ Normalizar los tensores a un rango de [0, 1]. """
    return data_tensor / 255.0


def split_data(data_tensor, labels_tensor, test_size=0.2, random_state=42):
    """ Dividir los datos en conjuntos de entrenamiento y validación. """
    X_train, X_val, y_train, y_val = train_test_split(
        data_tensor, labels_tensor, test_size=test_size, random_state=random_state
    )
    return X_train, X_val, y_train, y_val


def create_dataloaders(X_train, y_train, X_val, y_val, batch_size=64):
    """ Crear DataLoaders para los conjuntos de entrenamiento y validación. """
    train_dataset = TensorDataset(X_train, y_train)
    val_dataset = TensorDataset(X_val, y_val)
    train_loader = DataLoader(dataset=train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(dataset=val_dataset, batch_size=batch_size, shuffle=False)
    return train_loader, val_loader

#MAIN
def prep_data_main(annotated_patches_path, labeled_patients_path, annotated_images_dir):


    # Cargar metadata
    annotated_patches_df = load_metadata(annotated_patches_path)
    labeled_patients_df = load_metadata(labeled_patients_path)

    # Procesar imágenes anotadas
    patches_data = process_annotated_images(annotated_patches_df, annotated_images_dir)

    # Preparar el conjunto de datos
    patches_data_array, patches_labels_array = prepare_dataset(patches_data)


    # DATASET PREPROCESSING

    # Convertir arrays de Numpy a tensores de PyTorch
    patches_data_tensor, patches_labels_tensor = convert_to_tensors(patches_data_array, patches_labels_array)
    
    # Normalizar los datos si aún no lo están
    patches_data_tensor = normalize_tensors(patches_data_tensor)

    # Dividir los datos en entrenamiento y validación
    X_train, X_val, y_train, y_val = split_data(patches_data_tensor, patches_labels_tensor)

    # Crear DataLoaders
    train_loader, val_loader = create_dataloaders(X_train, y_train, X_val, y_val)
    
    return train_loader, val_loader