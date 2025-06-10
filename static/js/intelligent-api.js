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
