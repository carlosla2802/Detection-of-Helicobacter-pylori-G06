
import torch 
from sklearn.metrics import classification_report, confusion_matrix
from skimage.color import rgb2hsv
from sklearn.metrics import roc_curve, auc
import matplotlib.pyplot as plt
import numpy as np
import cv2 

def evaluate_reconstructions(model, pacients_data_tensors, device):
    model.eval()
    reconstructions = {}
    with torch.no_grad():
        for pacient in list(pacients_data_tensors.keys()):
            images_list = pacients_data_tensors[pacient]
            for image in images_list:
                image = image.to(device)
                reconstructed = model(image.unsqueeze(0))  # Añade una dimensión de lote (batch) de 1
                if pacient not in list(reconstructions.keys()):
                    reconstructions[pacient] = []
                reconstructions[pacient].append((image.squeeze().cpu(), reconstructed.squeeze().cpu()))
    return reconstructions

def visualize_reconstructions2(reconstructed_pacients_data_tensor):
    first_patient_images = reconstructed_pacients_data_tensor[list(reconstructed_pacients_data_tensor.keys())[6]]
    original_images = [pair[0].numpy().transpose(1, 2, 0) for pair in first_patient_images]
    reconstructed_images = [pair[1].numpy().transpose(1, 2, 0) for pair in first_patient_images]

    num_images = len(original_images)
    fig, axes = plt.subplots(nrows=num_images, ncols=2, figsize=(10, 2 * num_images))
    for i in range(num_images):
        # Visualización
        axes[i, 0].imshow(original_images[i])
        axes[i, 0].set_title('Original')
        axes[i, 0].axis('off')
        
        axes[i, 1].imshow(reconstructed_images[i])
        axes[i, 1].set_title('Reconstructed')
        axes[i, 1].axis('off')

    plt.show()


def detect_h_pylori(original_images, reconstructed_images, f_red_threshold, plot_img=False, pacient_id=False):
    # Reinvertir normalizacion
    original_images = (original_images * 255).numpy().transpose(1, 2, 0)
    reconstructed_images = (reconstructed_images * 255).numpy().transpose(1, 2, 0)

    # Convertir la imagen de RGB a HSV
    hsv_original_images = rgb2hsv(original_images)
    hue_hsv_original_images = hsv_original_images[:,:, 0]*255
    hsv_reconstructed_images = rgb2hsv(reconstructed_images)
    hue_hsv_reconstructed_images = hsv_reconstructed_images[:,:, 0]*255

    # Filtrar píxeles con tonalidades de color similares al rojo (en el rango [-20, 20] en el espacio de tonalidades)
    original_red_like_pixels_filter = (hue_hsv_original_images >= -20) & (hue_hsv_original_images <= 20)
    reconstructed_red_like_pixels_filter = (hue_hsv_reconstructed_images >= -20) & (hue_hsv_reconstructed_images<= 20)

    # Establece los píxeles fuera de la máscara en negro y convierte a rgb
    original_only_red = original_red_like_pixels_filter.copy() 
    reconstructed_only_red = reconstructed_red_like_pixels_filter.copy()   
    original_only_red = original_only_red.astype(int)
    reconstructed_only_red = reconstructed_only_red.astype(int)

    #Plot original/reconstructed images in hsv
    if plot_img and pacient_id=="B22-114":
        fig, axes = plt.subplots(nrows=3, ncols=2, figsize=(10, 2 * 2))

        axes[0,0].imshow(original_images.astype(np.uint8))
        axes[0,0].set_title('Original')
        axes[0,0].axis('off')

        axes[1,0].imshow(hsv_original_images, cmap='hsv')
        axes[1,0].set_title('Original hsv')
        axes[1,0].axis('off')

        axes[2,0].imshow(original_only_red, cmap='gray')
        axes[2,0].set_title('Original only red pixels')
        axes[2,0].axis('off')

        axes[0,1].imshow(reconstructed_images.astype(np.uint8))
        axes[0,1].set_title('Reconstructed')
        axes[0,1].axis('off')

        axes[1,1].imshow(hsv_reconstructed_images, cmap='hsv')
        axes[1,1].set_title('Reconstructed hsv')
        axes[1,1].axis('off')

        axes[2,1].imshow(reconstructed_only_red, cmap='gray')
        axes[2,1].set_title('Reconstructed only red pixels')
        axes[2,1].axis('off')

        plt.show()

    # Calcular la fracción de píxeles con tonalidades de color similares al rojo en las imágenes originales y reconstruidas
    f_red = compute_f_red(original_only_red, reconstructed_only_red)

    # Etiquetar la ventana como que contiene H. pylori si la fracción perdida (red_fraction_difference) es mayor que 1
    if f_red > f_red_threshold:
        return 1
    else:
        return -1
    

# Función para calcular la fracción de píxeles con tonalidades de color similares al rojo perdidos en la reconstrucción
def compute_f_red(original_only_red, reconstructed_only_red):
    
    # Calcular nº píxeles con tonalidades de color similares al rojo en las imágenes originales y reconstruidas
    red_pixels_original = np.count_nonzero(original_only_red)
    red_pixels_reconstructed = np.count_nonzero(reconstructed_only_red)

    # Calcular la diferencia de píxeles con tonalidades de color similares al rojo
    red_pixels_loss = red_pixels_original - red_pixels_reconstructed

    # Calcular Fred
    if red_pixels_original != 0:
        f_red = red_pixels_loss / red_pixels_original

    else:
        f_red = 0


    return f_red


def calculate_roc_curve_optimal_infected_windows_patient(real_labels, pacients_data_tensors, reconstructed_pacients_data_tensor, f_red_thresholds, prop_infected_thresholds, plot_img=False):
    real_values = list(real_labels.values())
    best_auc = -1
    best_combination = None
    all_scores = []

    # Iterar sobre todas las combinaciones de f_red_threshold y n_threshold
    for f_red_threshold in f_red_thresholds:
        for prop_infected_threshold in prop_infected_thresholds:
            pred_labels = detect_h_pylori_all_validation(pacients_data_tensors, reconstructed_pacients_data_tensor, f_red_threshold, prop_infected_threshold, plot_img)
            pred_values = list(pred_labels.values())

            fpr, tpr, _ = roc_curve(real_values, pred_values)
            current_auc = auc(fpr, tpr)

            # Guardar los puntajes y la combinación
            all_scores.append((current_auc, f_red_threshold, prop_infected_threshold))

            # Actualizar el mejor AUC y la mejor combinación
            if current_auc >= best_auc:
                best_auc = current_auc
                best_combination = (f_red_threshold, prop_infected_threshold)

    # Graficar la curva ROC para la mejor combinación
    if plot_img:
        plt.figure()
        fpr, tpr, _ = roc_curve(real_values, list(detect_h_pylori_all_validation(pacients_data_tensors, reconstructed_pacients_data_tensor, best_combination[0], best_combination[1], plot_img).values()))
        plt.plot(fpr, tpr, label=f'Mejor combinación: f_red_threshold = {best_combination[0]}, prop_infected_threshold = {best_combination[1]}, AUC = {best_auc:.2f}')
        plt.plot([0, 1], [0, 1], 'k--')  # Línea de referencia
        plt.xlabel('False Positive Rate (FPR)')
        plt.ylabel('True Positive Rate (TPR)')
        plt.title('ROC Curve')
        plt.legend(loc='lower right')
        plt.show()

    return best_combination


def detect_h_pylori_all_validation(pacients_data_tensors, reconstructed_pacients_data_tensor, f_red_threshold, prop_infected_threshold, plot_img=False):
    pred_labels = {}

    for pacient in list(pacients_data_tensors.keys()):
        pred_labels[pacient] = -1
        num_infected = 0
        for original_image, reconstructed_image in zip(pacients_data_tensors[pacient], reconstructed_pacients_data_tensor[pacient]):
            label = detect_h_pylori(original_image, reconstructed_image, f_red_threshold, plot_img, pacient_id=pacient)
            if label == 1:
                num_infected += 1
        
        prop_infected = num_infected / len(pacients_data_tensors[pacient])

        if prop_infected > prop_infected_threshold:
            pred_labels[pacient] = 1

    return pred_labels


def calculate_metrics(real_labels, pred_labels):
    # Mapeo de etiquetas: asumiendo que 1 es H. pylori y -1 es No H. pylori
    label_mapping = {1: "H. pylori", -1: "No H. pylori"}

    # Mapear las etiquetas reales y predichas
    real_values_mapped = [label_mapping[label] for label in real_labels.values()]
    pred_values_mapped = [label_mapping[label] for label in pred_labels.values()]

    report = classification_report(real_values_mapped, pred_values_mapped)

    # Calcula la matriz de confusión
    matrix = confusion_matrix(real_values_mapped, pred_values_mapped)
    tn, fp, fn, tp = matrix.ravel()

    # Formatea y presenta la matriz de confusión
    confusion_matrix_formatted = f"""
    Confusion Matrix:
    Ground Truth
    Predicted   H. pylori     No H. pylori
    H. pylori   {tp} (TP)     {fp} (FP)
    No H. pylori {fn} (FN)    {tn} (TN)
    """
    return report + "\n" +  confusion_matrix_formatted