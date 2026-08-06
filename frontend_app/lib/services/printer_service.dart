import 'dart:typed_data';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:blue_thermal_printer/blue_thermal_printer.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import 'package:image/image.dart' as img; // v4 Library

import '../models/shop_details.dart';

class PrinterService {
  final BlueThermalPrinter bluetooth = BlueThermalPrinter.instance;

  // Helper: Format quantity display with smart kg/gm conversion
  String _formatQuantityForPrint(String qtyDisplay, String unit) {
    // First apply short unit names
    String result = _shortenQtyDisplay(qtyDisplay);
    
    // Smart kg/gm conversion
    // Extract number from string like "0.4" or "1.2"
    final numMatch = RegExp(r'(\d+\.?\d*)').firstMatch(qtyDisplay);
    
    if (numMatch != null && unit.toLowerCase() == 'kg') {
      double value = double.tryParse(numMatch.group(1) ?? '0') ?? 0;
      
      // If < 1kg, convert to grams
      if (value > 0 && value < 1) {
        int grams = (value * 1000).round();
        return '${grams}gm';
      }
      // If > 1kg but has decimal, convert fully to grams
      else if (value > 1 && value != value.toInt()) {
        int grams = (value * 1000).round();
        return '${grams}gm';
      }
      // If whole kg, keep as is
      else if (value == value.toInt()) {
        return '${value.toInt()}kg';
      }
    }
    
    // Convert large grams to kg (e.g., 2000gm -> 2kg)
    if (unit.toLowerCase() == 'gm' || unit.toLowerCase() == 'gram') {
      final numMatch2 = RegExp(r'(\d+)').firstMatch(qtyDisplay);
      if (numMatch2 != null) {
        int gmValue = int.tryParse(numMatch2.group(1) ?? '0') ?? 0;
        if (gmValue >= 1000 && gmValue % 1000 == 0) {
          int kgValue = gmValue ~/ 1000;
          return '${kgValue}kg';
        }
      }
    }
    
    return result;
  }

  // Helper: Get short unit names
  String _getShortUnit(String unit) {
    final unitMap = {
      'dozen': 'doz',
      'plate': 'plt',
      'pieces': 'pic',
      'pics': 'pic',
      'litre': 'lit',
      'liter': 'lit',
    };
    return unitMap[unit.toLowerCase()] ?? unit;
  }

  // Helper: Format number without .0 for whole numbers
  String _formatNumber(double value) {
    if (value == value.toInt()) {
      return value.toInt().toString();
    }
    return value.toString();
  }

  // Helper: Shorten quantity display that already contains units
  String _shortenQtyDisplay(String qtyDisplay) {
    String result = qtyDisplay;
    result = result.replaceAll('dozen', 'doz');
    result = result.replaceAll('plate', 'plt');
    result = result.replaceAll('pieces', 'pic');
    result = result.replaceAll('pics', 'pic');
    result = result.replaceAll('litre', 'lit');
    result = result.replaceAll('liter', 'lit');
    return result;
  }

  Future<bool> isConnected() async {
    return (await bluetooth.isConnected) ?? false;
  }

  Future<String> printBill(
      Map<String, dynamic> billData, ShopDetails shopDetails, String? qrCodePath) async {
    if (!await isConnected()) {
      return "Printer not connected";
    }

    // DEBUG: Log received data
    if (kDebugMode) {
      print("🖨️ PRINTER SERVICE: Received bill data");
      print("🖨️ Bill ID: ${billData['id']}");
      print("🖨️ Items count: ${billData['items']?.length ?? 0}");
      print("🖨️ Items data: ${billData['items']}");
    }

    try {
      // 1. Setup PDF Document
      final doc = pw.Document();
      // 80mm width creates a high-res master that we scale down to 58mm later
      // This ensures text is crisp and not pixelated
      const pageFormat = PdfPageFormat(80 * PdfPageFormat.mm, double.infinity,
          marginAll: 2 * PdfPageFormat.mm);

      doc.addPage(pw.Page(
        pageFormat: pageFormat,
        build: (pw.Context context) {
          return pw.Column(
            crossAxisAlignment: pw.CrossAxisAlignment.start,
            mainAxisSize: pw.MainAxisSize.min,
            children: [
              // --- 1. BRANDING & HEADER ---
              pw.Center(
                  child: pw.Text("VYAMIT AI",
                      style: pw.TextStyle(
                          fontSize: 10,
                          fontWeight: pw.FontWeight.bold,
                          color: PdfColors.grey700))),
              pw.SizedBox(height: 2),

              pw.Center(
                  child: pw.Text(
                      (shopDetails.shopName.isNotEmpty
                              ? shopDetails.shopName
                              : "MY SHOP")
                          .toUpperCase(),
                      textAlign: pw.TextAlign.center,
                      style: pw.TextStyle(
                          fontWeight: pw.FontWeight.bold, fontSize: 22))),

              // Address & Phone
              pw.Center(
                  child: pw.Text(
                      shopDetails.address.isNotEmpty
                          ? shopDetails.address
                          : "Shop Address Here",
                      textAlign: pw.TextAlign.center,
                      style: const pw.TextStyle(fontSize: 12))),
              pw.Center(
                  child: pw.Text(
                      "Mob: ${shopDetails.phone1.isNotEmpty ? shopDetails.phone1 : '-'}",
                      style: const pw.TextStyle(fontSize: 12))),
              // Second phone number (only if exists)
              if (shopDetails.phone2.isNotEmpty)
                pw.Center(
                    child: pw.Text(
                        "Mob: ${shopDetails.phone2}",
                        style: const pw.TextStyle(fontSize: 12))),
              pw.Divider(thickness: 1),

              // --- 2. BILL META DATA ---
              pw.Row(
                  mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                  children: [
                    pw.Text(
                        "Bill No: ${billData['id']?.toString() ?? '001'}",
                        style: const pw.TextStyle(fontSize: 12)),
                    pw.Text("Date: ${billData['date'] ?? '-'}",
                        style: const pw.TextStyle(fontSize: 12)),
                  ]),
              pw.Row(
                  mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                  children: [
                    pw.Text("Cst: ${billData['customerName'] ?? 'Walk-in'}",
                        style: const pw.TextStyle(
                            fontSize: 12)),
                    pw.Text("Time: ${billData['time'] ?? '-'}",
                        style: const pw.TextStyle(fontSize: 12)),
                  ]),
              pw.Divider(thickness: 1),

              // --- 3. TABLE HEADERS (4 Columns) ---
              pw.Row(children: [
                pw.Expanded(
                    flex: 3,
                    child: pw.Text("Item",
                        style: const pw.TextStyle(fontSize: 12))),
                pw.Expanded(
                    flex: 2,
                    child: pw.Text("Qty",
                        textAlign: pw.TextAlign.center,
                        style: const pw.TextStyle(fontSize: 12))),
                pw.Expanded(
                    flex: 2,
                    child: pw.Text("Rate",
                        textAlign: pw.TextAlign.right,
                        style: const pw.TextStyle(fontSize: 12))),
                pw.Expanded(
                    flex: 2,
                    child: pw.Text("Price",
                        textAlign: pw.TextAlign.right,
                        style: const pw.TextStyle(fontSize: 12))),
              ]),
              pw.Divider(),

              // --- 4. ITEMS LIST (Smart Name Logic) ---
              ...billData['items'].map<pw.Widget>((item) {
                if (kDebugMode) {
                  print("🖨️ Processing item for print: $item");
                }
                
                // SMART NAME RESOLVER: Checks all possible keys so it never prints "Item"
                String itemName = "Item";
                if (item['name'] != null)
                  itemName = item['name'];
                else if (item['en'] != null)
                  itemName = item['en'];
                else if (item['names'] != null &&
                    item['names'] is List &&
                    (item['names'] as List).isNotEmpty)
                  itemName = item['names'][0];

                if (kDebugMode) {
                  print("🖨️ Item name resolved: $itemName");
                }

                // Extract quantity display - PRIORITIZE qty_display over qty
                String qtyDisplay = item['qty_display']?.toString() ?? 
                                   item['qty']?.toString() ?? "1kg";
                String unit = item['unit']?.toString() ?? 'kg';
                
                if (kDebugMode) {
                  print("🖨️ Raw qty_display: ${item['qty_display']}");
                  print("🖨️ Raw qty: ${item['qty']}");
                  print("🖨️ Using qtyDisplay: $qtyDisplay, Unit: $unit");
                }
                
                // Short unit names for printing
                String shortUnit = _getShortUnit(unit);
                
                // Format quantity with smart kg/gm conversion
                String formattedQty = _formatQuantityForPrint(qtyDisplay, unit);

                // Get rate and remove decimals if whole number
                double rateValue = (item['rate'] ?? item['price'] ?? 0).toDouble();
                String rateStr = _formatNumber(rateValue);
                String rateWithUnit = "$rateStr/$shortUnit";

                // Get total and remove decimals if whole number
                double totalValue = (item['total'] ?? 0).toDouble();
                String totalStr = "Rs${_formatNumber(totalValue)}";

                if (kDebugMode) {
                  print("🖨️ Printing: $itemName | $formattedQty | $rateWithUnit | $totalStr");
                }

                return pw.Padding(
                  padding: const pw.EdgeInsets.symmetric(vertical: 3),
                  child: pw.Row(children: [
                    // Item Name
                    pw.Expanded(
                        flex: 3,
                        child: pw.Text(itemName,
                            style: const pw.TextStyle(fontSize: 13))),
                    // Qty
                    pw.Expanded(
                        flex: 2,
                        child: pw.Text(formattedQty,
                            textAlign: pw.TextAlign.center,
                            style: const pw.TextStyle(fontSize: 13))),
                    // Rate (without Rs)
                    pw.Expanded(
                        flex: 2,
                        child: pw.Text(rateWithUnit,
                            textAlign: pw.TextAlign.right,
                            style: const pw.TextStyle(fontSize: 13))),
                    // Price (with Rs)
                    pw.Expanded(
                        flex: 2,
                        child: pw.Text(totalStr,
                            textAlign: pw.TextAlign.right,
                            style: const pw.TextStyle(fontSize: 13))),
                  ]),
                );
              }).toList(),

              pw.Divider(thickness: 1),

              // --- 5. TOTAL SECTION ---
              pw.Row(
                mainAxisAlignment: pw.MainAxisAlignment.end,
                children: [
                  pw.Text("Total Amount:  ",
                      style: const pw.TextStyle(fontSize: 14)),
                  pw.Text("Rs${_formatNumber((billData['total'] ?? 0).toDouble())}",
                      style: pw.TextStyle(
                          fontWeight: pw.FontWeight.bold, fontSize: 18)),
                ],
              ),
              pw.SizedBox(height: 10),

              // --- 6. FOOTER ---
              pw.Center(
                  child: pw.Text("Thank You! Visit Again",
                      style: const pw.TextStyle(fontSize: 14))),
              pw.SizedBox(height: 5),
              
              // QR Code (if exists)
              if (qrCodePath != null && qrCodePath.isNotEmpty)
                pw.Column(children: [
                  pw.SizedBox(height: 10),
                  pw.Center(
                    child: pw.Container(
                      width: 150,
                      height: 150,
                      child: pw.Image(
                        pw.MemoryImage(
                          File(qrCodePath).readAsBytesSync(),
                        ),
                        fit: pw.BoxFit.contain,
                      ),
                    ),
                  ),
                  pw.SizedBox(height: 5),
                  pw.Center(
                    child: pw.Text("Scan to Pay",
                        style: const pw.TextStyle(fontSize: 10)),
                  ),
                  pw.SizedBox(height: 10),
                ]),
              
              pw.Center(
                  child: pw.Text("Powered by Vyamit AI",
                      style: const pw.TextStyle(
                          fontSize: 10, color: PdfColors.grey600))),
              pw.SizedBox(height: 20),
            ],
          );
        },
      ));

      // 3. Rasterize (Convert PDF to Image)
      await for (final page
          in Printing.raster(await doc.save(), pages: [0], dpi: 203)) {
        final Uint8List imageBytes = await page.toPng();
        final img.Image? originalImage = img.decodeImage(imageBytes);

        if (originalImage != null) {
          // A. Resize to 384px (Standard Thermal Width)
          final img.Image resizedImage =
              img.copyResize(originalImage, width: 384);

          // B. Initialize Printer
          await bluetooth.writeBytes(Uint8List.fromList([0x1b, 0x40]));
          await Future.delayed(const Duration(milliseconds: 100));

          // C. Send Image (Using the Fixed Transparent/Black Logic)
          final List<int> printBytes = _generateRasterData(resizedImage);
          await bluetooth.writeBytes(Uint8List.fromList(printBytes));

          // D. Feed & Cut
          await Future.delayed(const Duration(milliseconds: 100));
          await bluetooth.writeBytes(Uint8List.fromList([0x0a, 0x0a, 0x0a]));
        }
        break;
      }
      return "Success";
    } catch (e) {
      return "Print Error: $e";
    }
  }

  // --- BIT PACKING (Fixed Black Background & Transparency) ---
  List<int> _generateRasterData(img.Image src) {
    List<int> data = [];
    int width = src.width;
    int height = src.height;

    // Header: GS v 0 0
    data.addAll([0x1d, 0x76, 0x30, 0x00]);

    int widthBytes = (width + 7) ~/ 8;
    data.add(widthBytes % 256);
    data.add(widthBytes ~/ 256);
    data.add(height % 256);
    data.add(height ~/ 256);

    for (int y = 0; y < height; y++) {
      for (int x = 0; x < widthBytes; x++) {
        int byte = 0;
        for (int k = 0; k < 8; k++) {
          int pixelX = x * 8 + k;
          if (pixelX < width) {
            final pixel = src.getPixel(pixelX, y);

            // 1. Check Transparency (Ignore background)
            if (pixel.a == 0) continue;

            // 2. Check Brightness (Dark pixels = 1, Light pixels = 0)
            double brightness = img.getLuminance(pixel).toDouble();
            if (brightness <= 1.0) brightness *= 255;

            if (brightness < 128) {
              byte |= (1 << (7 - k));
            }
          }
        }
        data.add(byte);
      }
    }
    return data;
  }
}
