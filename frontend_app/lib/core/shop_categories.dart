/// Canonical profile category names. Must match backend `core.shop_categories`.
const String kDefaultShopCategory = 'General';

const List<String> kShopCategories = [
  'Kirana',
  'Stationery',
  'Pharmacy',
  'Doctor Prescription',
  'Dairy',
  'Hardware',
  'Fast Food',
  'General',
  'Clothing',
  'Other',
];

String _categoryKey(String value) =>
    value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), '');

/// Maps legacy values and common spelling variants to one storage value.
/// The API remains the authority and returns the same canonical names.
String canonicalShopCategory(String? value) {
  if (value == null || value.trim().isEmpty) return kDefaultShopCategory;

  final key = _categoryKey(value.trim());
  for (final category in kShopCategories) {
    if (_categoryKey(category) == key) return category;
  }

  const aliases = <String, String>{
    'stationary': 'Stationery',
    'staationary': 'Stationery',
    'medical': 'Pharmacy',
    'doctor': 'Doctor Prescription',
    'prescription': 'Doctor Prescription',
    'restaurant': 'Fast Food',
    'fastfood': 'Fast Food',
  };
  return aliases[key] ?? kDefaultShopCategory;
}
