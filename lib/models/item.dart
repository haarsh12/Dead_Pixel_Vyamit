class Item {
  final String id; // Database ID
  final List<String> names; // ["Rice", "Chawal", "Tandul"]
  final double price;
  final String unit; // "kg", "pkt"
  final String category; // "Anaaj", "Masale"

  Item({
    required this.id,
    required this.names,
    required this.price,
    required this.unit,
    required this.category,
  });

  // Convert JSON from Backend -> Flutter Object
  factory Item.fromJson(Map<String, dynamic> json) {
    return Item(
      id: json['_id'] ??
          json['id']?.toString() ??
          '', // Handle both MongoDB _id and SQL id
      names: List<String>.from(json['names'] ?? []),
      price: (json['price'] as num?)?.toDouble() ?? 0.0,
      unit: json['unit'] ?? 'kg',
      category: json['category'] ?? 'General',
    );
  }

  // Convert Flutter Object -> JSON for Backend
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'names': names,
      'price': price,
      'unit': unit,
      'category': category,
    };
  }
}

