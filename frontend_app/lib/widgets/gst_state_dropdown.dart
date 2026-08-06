import 'package:flutter/material.dart';

const List<String> kIndianStatesAndUnionTerritories = [
  'Andaman and Nicobar Islands',
  'Andhra Pradesh',
  'Arunachal Pradesh',
  'Assam',
  'Bihar',
  'Chandigarh',
  'Chhattisgarh',
  'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi',
  'Goa',
  'Gujarat',
  'Haryana',
  'Himachal Pradesh',
  'Jammu and Kashmir',
  'Jharkhand',
  'Karnataka',
  'Kerala',
  'Ladakh',
  'Lakshadweep',
  'Madhya Pradesh',
  'Maharashtra',
  'Manipur',
  'Meghalaya',
  'Mizoram',
  'Nagaland',
  'Odisha',
  'Puducherry',
  'Punjab',
  'Rajasthan',
  'Sikkim',
  'Tamil Nadu',
  'Telangana',
  'Tripura',
  'Uttar Pradesh',
  'Uttarakhand',
  'West Bengal',
];

class GstStateDropdown extends StatelessWidget {
  final String label;
  final String? value;
  final ValueChanged<String?> onChanged;

  const GstStateDropdown({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      value: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: '$label *'),
      items: kIndianStatesAndUnionTerritories
          .map(
            (state) => DropdownMenuItem<String>(
              value: state,
              child: Text(state, overflow: TextOverflow.ellipsis),
            ),
          )
          .toList(),
      onChanged: onChanged,
      validator: (selectedState) {
        if (selectedState == null || selectedState.isEmpty) {
          return 'Please select ${label.toLowerCase()}';
        }
        return null;
      },
    );
  }
}
