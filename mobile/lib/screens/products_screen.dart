import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/setu_provider.dart';

class ProductsScreen extends StatefulWidget {
  final VoidCallback? onOrderPlaced;

  const ProductsScreen({super.key, this.onOrderPlaced});

  @override
  State<ProductsScreen> createState() => _ProductsScreenState();
}

class _ProductsScreenState extends State<ProductsScreen> {
  List<Map<String, dynamic>> _products = [];
  bool _isLoading = true;
  String? _error;
  String _selectedCategory = 'All';

  @override
  void initState() {
    super.initState();
    _fetchProducts();
  }

  Future<void> _fetchProducts() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    final provider = Provider.of<SetuProvider>(context, listen: false);
    try {
      final list = await provider.apiService.getProducts();
      if (!mounted) return;
      setState(() {
        _products = list;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Failed to load products catalogue.';
        _isLoading = false;
      });
    }
  }

  List<String> get _categories {
    final cats = <String>{'All'};
    for (final p in _products) {
      final c = p['category']?.toString();
      if (c != null && c.isNotEmpty) cats.add(c);
    }
    return cats.toList();
  }

  List<Map<String, dynamic>> get _filteredProducts {
    if (_selectedCategory == 'All') return _products;
    return _products.where((p) => p['category']?.toString() == _selectedCategory).toList();
  }

  void _openOrderSheet(Map<String, dynamic> product) {
    final provider = Provider.of<SetuProvider>(context, listen: false);
    final addressController = TextEditingController(
      text: '${provider.farmName.isNotEmpty ? provider.farmName : "My Farm"}, ${provider.region}',
    );
    final notesController = TextEditingController();
    int quantity = 1;
    String paymentMethod = 'UPI';
    bool isSubmitting = false;

    final priceMinor = (product['price_minor_units'] as num?)?.toInt() ?? 0;
    final priceRupees = priceMinor > 0 ? (priceMinor / 100).toStringAsFixed(2) : (product['price']?.toString() ?? '0');

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (modalCtx) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            final totalAmount = (priceMinor * quantity / 100).toStringAsFixed(2);

            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: const Color(0xFFE8F5E9),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: const Icon(Icons.shopping_bag_outlined, color: Color(0xFF2E7D32), size: 22),
                            ),
                            const SizedBox(width: 10),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'Order Hardware',
                                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Color(0xFF1B5E20)),
                                ),
                                Text(
                                  product['name'] ?? 'Product',
                                  style: const TextStyle(fontSize: 12, color: Color(0xFF5A695C), fontWeight: FontWeight.w600),
                                ),
                              ],
                            ),
                          ],
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, size: 20),
                          onPressed: () => Navigator.pop(modalCtx),
                        ),
                      ],
                    ),
                    const Divider(height: 24),

                    // Price and Quantity summary
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Unit Price', style: TextStyle(fontSize: 11, color: Colors.grey)),
                            Text('₹$priceRupees', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF1B5E20))),
                          ],
                        ),
                        Row(
                          children: [
                            IconButton.outlined(
                              visualDensity: VisualDensity.compact,
                              icon: const Icon(Icons.remove, size: 16),
                              onPressed: quantity > 1 ? () => setSheetState(() => quantity--) : null,
                            ),
                            Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 10),
                              child: Text('$quantity', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                            ),
                            IconButton.outlined(
                              visualDensity: VisualDensity.compact,
                              icon: const Icon(Icons.add, size: 16),
                              onPressed: () => setSheetState(() => quantity++),
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),

                    // Delivery Address
                    TextField(
                      controller: addressController,
                      decoration: InputDecoration(
                        labelText: 'Delivery Address / Shed Location *',
                        prefixIcon: const Icon(Icons.location_on_outlined, color: Color(0xFF2E7D32), size: 19),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        contentPadding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                      ),
                      maxLines: 2,
                    ),
                    const SizedBox(height: 12),

                    // Payment Method selector
                    DropdownButtonFormField<String>(
                      initialValue: paymentMethod,
                      decoration: InputDecoration(
                        labelText: 'Payment Method',
                        prefixIcon: const Icon(Icons.payment_outlined, color: Color(0xFF2E7D32), size: 19),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        contentPadding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'UPI', child: Text('UPI / QR Code')),
                        DropdownMenuItem(value: 'COD', child: Text('Cash on Delivery (Pay on Arrival)')),
                        DropdownMenuItem(value: 'CARD', child: Text('Debit / Credit Card')),
                      ],
                      onChanged: (val) {
                        if (val != null) setSheetState(() => paymentMethod = val);
                      },
                    ),
                    const SizedBox(height: 12),

                    // Delivery Notes
                    TextField(
                      controller: notesController,
                      decoration: InputDecoration(
                        labelText: 'Delivery Instructions (Optional)',
                        hintText: 'e.g. Call before arrival, near main mulberry field',
                        prefixIcon: const Icon(Icons.notes_outlined, color: Colors.grey, size: 19),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                        contentPadding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                      ),
                    ),
                    const SizedBox(height: 18),

                    // Total & Confirm button
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Total Payable:', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                        Text('₹$totalAmount', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Color(0xFF2E7D32))),
                      ],
                    ),
                    const SizedBox(height: 12),

                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF2E7D32),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 13),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: isSubmitting
                          ? null
                          : () async {
                              final address = addressController.text.trim();
                              if (address.isEmpty) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('Please provide a delivery address.')),
                                );
                                return;
                              }

                              setSheetState(() => isSubmitting = true);
                              final res = await provider.apiService.placeOrder(
                                items: [
                                  {
                                    'product_id': product['id'],
                                    'quantity': quantity,
                                  }
                                ],
                                shippingAddress: address,
                                paymentMethod: paymentMethod,
                                notes: notesController.text.trim(),
                              );

                              if (!modalCtx.mounted || !mounted) return;
                              if (res['success'] == true) {
                                Navigator.pop(modalCtx);
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text('Order placed successfully! Tracking hardware shipment.'),
                                    backgroundColor: Color(0xFF2E7D32),
                                  ),
                                );
                                widget.onOrderPlaced?.call();
                              } else {
                                setSheetState(() => isSubmitting = false);
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(res['error']?.toString() ?? 'Failed to place order.'),
                                    backgroundColor: const Color(0xFFC62828),
                                  ),
                                );
                              }
                            },
                      child: isSubmitting
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Text(
                              'Confirm & Place Order',
                              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
                            ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: Color(0xFF2E7D32)));
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.grey),
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: Colors.grey, fontWeight: FontWeight.w600)),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: _fetchProducts,
              child: const Text('Try Again'),
            ),
          ],
        ),
      );
    }

    final products = _filteredProducts;

    return RefreshIndicator(
      onRefresh: _fetchProducts,
      color: const Color(0xFF2E7D32),
      child: Column(
        children: [
          // Category Filter Chips
          if (_categories.length > 1)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
              color: Colors.white,
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: _categories.map((cat) {
                    final isSel = cat == _selectedCategory;
                    return Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                        label: Text(cat, style: TextStyle(fontSize: 12, fontWeight: isSel ? FontWeight.w700 : FontWeight.w500)),
                        selected: isSel,
                        selectedColor: const Color(0xFFE8F5E9),
                        onSelected: (_) {
                          setState(() => _selectedCategory = cat);
                        },
                      ),
                    );
                  }).toList(),
                ),
              ),
            ),

          Expanded(
            child: products.isEmpty
                ? const Center(
                    child: Text('No hardware products found in this category.', style: TextStyle(color: Colors.grey)),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: products.length,
                    itemBuilder: (context, index) {
                      final p = products[index];
                      final priceMinor = (p['price_minor_units'] as num?)?.toInt() ?? 0;
                      final priceFormatted = priceMinor > 0 ? (priceMinor / 100).toStringAsFixed(0) : (p['price']?.toString() ?? '0');
                      final stock = (p['stock_quantity'] as num?)?.toInt() ?? 0;
                      final inStock = stock > 0;
                      final category = p['category'] ?? 'Hardware';

                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        elevation: 1,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Container(
                                    width: 60,
                                    height: 60,
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFE8F5E9),
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: const Icon(Icons.sensors_rounded, size: 32, color: Color(0xFF2E7D32)),
                                  ),
                                  const SizedBox(width: 14),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: const Color(0xFFF1F8E9),
                                            borderRadius: BorderRadius.circular(6),
                                          ),
                                          child: Text(
                                            category.toString().toUpperCase(),
                                            style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.bold, color: Color(0xFF33691E)),
                                          ),
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          p['name'] ?? 'Setu Hardware',
                                          style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w700, color: Color(0xFF1B5E20)),
                                        ),
                                        if (p['description'] != null)
                                          Text(
                                            p['description'],
                                            maxLines: 2,
                                            overflow: TextOverflow.ellipsis,
                                            style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600),
                                          ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                              const Divider(height: 20),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        '₹$priceFormatted',
                                        style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: Color(0xFF1B5E20)),
                                      ),
                                      Row(
                                        children: [
                                          Icon(
                                            inStock ? Icons.check_circle_outline : Icons.highlight_off,
                                            size: 13,
                                            color: inStock ? Colors.green.shade700 : Colors.red,
                                          ),
                                          const SizedBox(width: 3),
                                          Text(
                                            inStock ? 'In Stock ($stock units)' : 'Out of Stock',
                                            style: TextStyle(fontSize: 10.5, color: inStock ? Colors.green.shade700 : Colors.red, fontWeight: FontWeight.w600),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                  ElevatedButton.icon(
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: const Color(0xFF2E7D32),
                                      foregroundColor: Colors.white,
                                      elevation: 0,
                                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                    ),
                                    onPressed: inStock ? () => _openOrderSheet(p) : null,
                                    icon: const Icon(Icons.add_shopping_cart, size: 16),
                                    label: const Text('Order Now', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
