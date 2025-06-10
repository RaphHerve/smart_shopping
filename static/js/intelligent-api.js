/**
 * Client API pour les fonctionnalités intelligentes Smart Shopping
 */

class SmartShoppingIntelligentAPI {
    constructor() {
        this.baseURL = '';  // Même domaine que Flask
    }

    /**
     * Recherche de recettes via API Jow
     */
    async searchJowRecipes(query, options = {}) {
        try {
            const response = await fetch(`${this.baseURL}/api/intelligent/search-recipes`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    limit: options.limit || 10,
                    ...options
                })
            });

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Erreur lors de la recherche');
            }

            return data.data.recipes;
        } catch (error) {
            console.error('Erreur recherche recettes:', error);
            throw error;
        }
    }

    /**
     * Consolidation intelligente des ingrédients
     */
    async consolidateIngredients(recipes) {
        try {
            const response = await fetch(`${this.baseURL}/api/intelligent/consolidate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    recipes: recipes
                })
            });

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Erreur lors de la consolidation');
            }

            return data.data;
        } catch (error) {
            console.error('Erreur consolidation:', error);
            throw error;
        }
    }

    /**
     * Obtenir des suggestions intelligentes
     */
    async getIntelligentSuggestions(ingredient, context = {}) {
        try {
            const response = await fetch(`${this.baseURL}/api/intelligent/suggestions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ingredient: ingredient,
                    context: context
                })
            });

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Erreur lors de la génération des suggestions');
            }

            return data.data.suggestions;
        } catch (error) {
            console.error('Erreur suggestions:', error);
            throw error;
        }
    }

    /**
     * Ajouter un ingrédient à la liste de courses principale
     */
    async addToMainShoppingList(name, category = 'Recettes', quantity = 1) {
        try {
            const response = await fetch(`${this.baseURL}/api/shopping-list`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: name,
                    category: category,
                    quantity: quantity
                })
            });

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Erreur ajout à la liste:', error);
            throw error;
        }
    }

    /**
     * Utilitaire pour normaliser les noms d'ingrédients côté client
     */
    normalizeIngredientName(name) {
        return name
            .toLowerCase()
            .trim()
            .replace(/[àáâãäå]/g, 'a')
            .replace(/[èéêë]/g, 'e')
            .replace(/[ìíîï]/g, 'i')
            .replace(/[òóôõö]/g, 'o')
            .replace(/[ùúûü]/g, 'u')
            .replace(/[ç]/g, 'c')
            .replace(/[ñ]/g, 'n')
            .replace(/\s+/g, ' ')
            .replace(/[^\w\s]/g, '');
    }

    /**
     * Détecter les doublons côté client
     */
    detectDuplicates(ingredients) {
        const normalized = {};
        const duplicates = [];

        for (const ingredient of ingredients) {
            const normalizedName = this.normalizeIngredientName(ingredient.name);
            
            if (normalized[normalizedName]) {
               // Doublon détecté
               duplicates.push({
                   original: normalized[normalizedName],
                   duplicate: ingredient,
                   normalizedName: normalizedName
               });
           } else {
               normalized[normalizedName] = ingredient;
           }
       }

       return {
           unique: Object.values(normalized),
           duplicates: duplicates
       };
   }

   /**
    * Convertir les unités côté client
    */
   convertUnits(quantity, fromUnit, toUnit) {
       const conversions = {
           // Poids
           'kg_to_g': 1000,
           'g_to_kg': 0.001,
           'mg_to_g': 0.001,
           'g_to_mg': 1000,
           
           // Volume
           'l_to_ml': 1000,
           'ml_to_l': 0.001,
           'cl_to_ml': 10,
           'ml_to_cl': 0.1,
           'dl_to_ml': 100,
           'ml_to_dl': 0.01,
           
           // Cuisine
           'cuillere_soupe_to_ml': 15,
           'cuillere_cafe_to_ml': 5,
           'tasse_to_ml': 250,
           'verre_to_ml': 200
       };

       const conversionKey = `${fromUnit.toLowerCase()}_to_${toUnit.toLowerCase()}`;
       const factor = conversions[conversionKey];

       if (factor) {
           return quantity * factor;
       }

       return quantity; // Pas de conversion possible
   }

   /**
    * Formater l'affichage des quantités
    */
   formatQuantity(quantity, unit) {
       // Arrondir à 2 décimales maximum
       const rounded = Math.round(quantity * 100) / 100;
       
       // Formater selon l'unité
       if (unit === 'g' && rounded >= 1000) {
           return `${rounded / 1000} kg`;
       }
       
       if (unit === 'ml' && rounded >= 1000) {
           return `${rounded / 1000} l`;
       }
       
       return `${rounded} ${unit}`;
   }

   /**
    * Valider une recette avant traitement
    */
   validateRecipe(recipe) {
       const errors = [];

       if (!recipe.name || recipe.name.trim() === '') {
           errors.push('Le nom de la recette est requis');
       }

       if (!recipe.ingredients || recipe.ingredients.length === 0) {
           errors.push('Au moins un ingrédient est requis');
       }

       if (recipe.ingredients) {
           recipe.ingredients.forEach((ingredient, index) => {
               if (!ingredient.name || ingredient.name.trim() === '') {
                   errors.push(`L'ingrédient ${index + 1} doit avoir un nom`);
               }
               
               if (ingredient.quantity && (isNaN(ingredient.quantity) || ingredient.quantity <= 0)) {
                   errors.push(`L'ingrédient ${index + 1} doit avoir une quantité positive`);
               }
           });
       }

       return {
           isValid: errors.length === 0,
           errors: errors
       };
   }

   /**
    * Calculer les statistiques d'une liste consolidée
    */
   calculateStats(consolidatedList) {
       if (!consolidatedList || !consolidatedList.items) {
           return {
               totalItems: 0,
               consolidatedItems: 0,
               totalRecipes: 0,
               averageIngredientsPerRecipe: 0
           };
       }

       const items = consolidatedList.items;
       const consolidatedItems = items.filter(item => item.isConsolidated);
       const allRecipes = new Set();

       items.forEach(item => {
           if (item.recipes) {
               item.recipes.forEach(recipe => allRecipes.add(recipe));
           }
       });

       return {
           totalItems: items.length,
           consolidatedItems: consolidatedItems.length,
           totalRecipes: allRecipes.size,
           averageIngredientsPerRecipe: allRecipes.size > 0 ? (items.length / allRecipes.size).toFixed(1) : 0,
           consolidationRate: items.length > 0 ? ((consolidatedItems.length / items.length) * 100).toFixed(1) : 0
       };
   }
}

// Utilitaires pour l'interface
class UIHelpers {
   
   /**
    * Afficher une notification toast
    */
   static showToast(message, type = 'info', duration = 4000) {
       const toast = document.createElement('div');
       toast.className = `toast toast-${type}`;
       toast.innerHTML = `
           <div class="toast-content">
               <span class="toast-icon">${this.getToastIcon(type)}</span>
               <span class="toast-message">${message}</span>
               <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
           </div>
       `;

       // Styles inline pour le toast
       toast.style.cssText = `
           position: fixed;
           top: 20px;
           right: 20px;
           background: ${this.getToastColor(type)};
           color: white;
           padding: 15px 20px;
           border-radius: 8px;
           box-shadow: 0 4px 12px rgba(0,0,0,0.2);
           z-index: 1000;
           animation: slideInRight 0.3s ease-out;
           max-width: 400px;
       `;

       document.body.appendChild(toast);

       // Suppression automatique
       if (duration > 0) {
           setTimeout(() => {
               if (toast.parentElement) {
                   toast.remove();
               }
           }, duration);
       }
   }

   static getToastIcon(type) {
       const icons = {
           'success': '✅',
           'error': '❌',
           'warning': '⚠️',
           'info': 'ℹ️'
       };
       return icons[type] || 'ℹ️';
   }

   static getToastColor(type) {
       const colors = {
           'success': '#10b981',
           'error': '#ef4444',
           'warning': '#f59e0b',
           'info': '#3b82f6'
       };
       return colors[type] || '#3b82f6';
   }

   /**
    * Créer un loader
    */
   static createLoader(text = 'Chargement...') {
       const loader = document.createElement('div');
       loader.className = 'smart-loader';
       loader.innerHTML = `
           <div class="loader-content">
               <div class="spinner"></div>
               <span>${text}</span>
           </div>
       `;

       loader.style.cssText = `
           position: fixed;
           top: 0;
           left: 0;
           width: 100%;
           height: 100%;
           background: rgba(0,0,0,0.5);
           display: flex;
           justify-content: center;
           align-items: center;
           z-index: 9999;
       `;

       return loader;
   }

   /**
    * Debounce pour optimiser les recherches
    */
   static debounce(func, wait) {
       let timeout;
       return function executedFunction(...args) {
           const later = () => {
               clearTimeout(timeout);
               func(...args);
           };
           clearTimeout(timeout);
           timeout = setTimeout(later, wait);
       };
   }

   /**
    * Formater les dates
    */
   static formatDate(date) {
       if (!(date instanceof Date)) {
           date = new Date(date);
       }
       
       return date.toLocaleDateString('fr-FR', {
           year: 'numeric',
           month: 'long',
           day: 'numeric'
       });
   }

   /**
    * Valider un email
    */
   static isValidEmail(email) {
       const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
       return emailRegex.test(email);
   }

   /**
    * Générer un ID unique
    */
   static generateId() {
       return Date.now().toString(36) + Math.random().toString(36).substr(2);
   }
}

// Export pour utilisation dans les modules
if (typeof module !== 'undefined' && module.exports) {
   module.exports = { SmartShoppingIntelligentAPI, UIHelpers };
}

// Instance globale pour utilisation directe
window.SmartShoppingIntelligentAPI = SmartShoppingIntelligentAPI;
window.UIHelpers = UIHelpers;

// Auto-initialisation
document.addEventListener('DOMContentLoaded', function() {
   // Ajouter les styles CSS nécessaires
   const styles = document.createElement('style');
   styles.textContent = `
       @keyframes slideInRight {
           from {
               opacity: 0;
               transform: translateX(100%);
           }
           to {
               opacity: 1;
               transform: translateX(0);
           }
       }

       .spinner {
           width: 40px;
           height: 40px;
           border: 4px solid #f3f3f3;
           border-top: 4px solid #3498db;
           border-radius: 50%;
           animation: spin 1s linear infinite;
           margin-bottom: 10px;
       }

       @keyframes spin {
           0% { transform: rotate(0deg); }
           100% { transform: rotate(360deg); }
       }

       .loader-content {
           background: white;
           padding: 30px;
           border-radius: 10px;
           text-align: center;
           box-shadow: 0 4px 20px rgba(0,0,0,0.3);
       }

       .toast-content {
           display: flex;
           align-items: center;
           gap: 10px;
       }

       .toast-close {
           background: none;
           border: none;
           color: white;
           font-size: 18px;
           cursor: pointer;
           padding: 0;
           margin-left: auto;
       }

       .toast-close:hover {
           opacity: 0.8;
       }
   `;
   document.head.appendChild(styles);
});
