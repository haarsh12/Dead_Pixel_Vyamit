import 'package:flutter/material.dart';
import '../models/item.dart';
import '../services/inventory_service.dart';

class InventoryProvider with ChangeNotifier {
  final InventoryService _service = InventoryService();

  // Start with empty inventory
  List<Item> _items = [];
  final Map<String, double?> _localGstRates = {};
  
  // Predefined categories that persist even when empty
  List<String> _categories = [
    'Anaaj',
    'Atta',
    'Dal',
    'Masale',
    'Tel',
    'Dry Fruits',
    'Upvas',
    'Other'
  ];

  bool _isLoading = false;
  String _selectedCategory = 'Anaaj';

  List<Item> get items => _items;
  List<String> get categories => _categories;
  bool get isLoading => _isLoading;
  String get selectedCategory => _selectedCategory;

  double? gstRateForItemName(String name) {
    final normalizedName = name.trim().toLowerCase();
    for (final item in _items) {
      if (item.names.any((alias) => alias.trim().toLowerCase() == normalizedName)) {
        return item.gstRate;
      }
    }
    return null;
  }

  // Filter Logic for Display
  List<Item> getFilteredItems(String searchQuery) {
    if (searchQuery.isEmpty) {
      return _items.where((i) => i.category == _selectedCategory).toList();
    } else {
      return _items
          .where((i) => i.names
              .any((n) => n.toLowerCase().contains(searchQuery.toLowerCase())))
          .toList();
    }
  }

  void setCategory(String category) {
    _selectedCategory = category;
    notifyListeners();
  }

  // Add a new category
  void addCategory(String categoryName) {
    if (!_categories.contains(categoryName)) {
      _categories.add(categoryName);
      notifyListeners();
    }
  }

  // Delete a category and all its items
  Future<void> deleteCategory(String categoryName) async {
    try {
      print("🗑️ Deleting category: $categoryName");
      
      // Get all items in this category
      final itemsToDelete = _items.where((i) => i.category == categoryName).toList();
      
      // Delete all items from backend
      for (var item in itemsToDelete) {
        await _service.deleteItem(item.id);
      }
      
      // Remove items from local list
      _items.removeWhere((i) => i.category == categoryName);
      
      // Remove category
      _categories.remove(categoryName);
      
      // Switch to first available category if current was deleted
      if (_selectedCategory == categoryName && _categories.isNotEmpty) {
        _selectedCategory = _categories.first;
      }
      
      notifyListeners();
      print("✅ Category deleted: $categoryName");
    } catch (e) {
      print("❌ Delete Category Error: $e");
      rethrow;
    }
  }

  // Fetch items from backend
  Future<void> fetchItems() async {
    _isLoading = true;
    notifyListeners();

    try {
      print("📥 Fetching items from backend...");
      final backendItems = await _service.getItems();
      print("✅ Fetched ${backendItems.length} items from backend");

      _items = backendItems.map((backendItem) {
        final gstRate = _localGstRates[backendItem.id] ?? backendItem.gstRate;
        return backendItem.copyWith(gstRate: gstRate);
      }).toList();
      
      // Add any custom categories from backend items that aren't in predefined list
      for (var item in backendItems) {
        if (!_categories.contains(item.category)) {
          _categories.add(item.category);
        }
      }
    } catch (e) {
      print("❌ Error fetching items: $e");
    }

    _isLoading = false;
    notifyListeners();
  }

  // Add or Update item
  Future<void> addItem(Item newItem) async {
    try {
      print("💾 Saving item: ${newItem.id} (${newItem.names[0]}) - ₹${newItem.price}");
      print("   Category: ${newItem.category}, Unit: ${newItem.unit}");

      // Call backend (POST endpoint handles upsert based on ID)
      final backendSavedItem = await _service.addItem(newItem);
      final savedItem = backendSavedItem.copyWith(gstRate: newItem.gstRate);
      _localGstRates[savedItem.id] = newItem.gstRate;
      print("✅ Backend saved item with ID: ${savedItem.id}");

      // Update local state - find by ID
      final index = _items.indexWhere((i) => i.id == newItem.id);
      if (index != -1) {
        _items[index] = savedItem;
        print("✅ Updated local item at index $index: ${savedItem.names[0]}");
      } else {
        _items.add(savedItem);
        print("✅ Added new local item: ${savedItem.names[0]}");
      }

      // Add category if it's new
      if (!_categories.contains(newItem.category)) {
        _categories.add(newItem.category);
      }

      notifyListeners();
    } catch (e) {
      print("❌ Save Error: $e");
      await fetchItems();
    }
  }

  // Delete item
  Future<void> deleteItem(String id) async {
    try {
      print("🗑️ Deleting item: $id");

      // Delete from backend
      await _service.deleteItem(id);
      
      // Remove from local list
      _items.removeWhere((i) => i.id == id);
      _localGstRates.remove(id);
      
      notifyListeners();
      print("✅ Deleted from backend");
    } catch (e) {
      print("❌ Delete Error: $e");
      rethrow;
    }
  }
}
