class GstBillingDetails {
  final String gstin;
  final String businessAddress;
  final String city;
  final String state;
  final String placeOfSupply;
  final String invoicePrefix;
  final GstCalculationMode calculationMode;

  const GstBillingDetails({
    required this.gstin,
    required this.businessAddress,
    required this.city,
    required this.state,
    required this.placeOfSupply,
    required this.invoicePrefix,
    required this.calculationMode,
  });
}

enum GstCalculationMode {
  cgstSgst,
  igst,
}
