import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/setu_provider.dart';

class OrdersScreen extends StatefulWidget {
  final VoidCallback? onBrowseProducts;

  const OrdersScreen({super.key, this.onBrowseProducts});

  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  List<Map<String, dynamic>> _orders = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchOrders();
  }

  Future<void> _fetchOrders() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    final provider = Provider.of<SetuProvider>(context, listen: false);
    try {
      final list = await provider.apiService.getOrders();
      if (!mounted) return;
      setState(() {
        _orders = list;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Failed to load orders history.';
        _isLoading = false;
      });
    }
  }

  Color _statusColor(String status) {
    switch (status.toUpperCase()) {
      case 'PAID':
      case 'FULFILLED':
      case 'DELIVERED':
        return const Color(0xFF2E7D32);
      case 'PROCESSING':
      case 'SHIPPED':
        return const Color(0xFF1976D2);
      case 'PENDING':
      case 'PAYMENT_PENDING':
        return const Color(0xFFF57C00);
      case 'CANCELLED':
      case 'REFUNDED':
        return const Color(0xFFD32F2F);
      default:
        return Colors.blueGrey;
    }
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
            const Icon(Icons.receipt_long_outlined, size: 48, color: Colors.grey),
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: Colors.grey, fontWeight: FontWeight.w600)),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: _fetchOrders,
              child: const Text('Try Again'),
            ),
          ],
        ),
      );
    }

    if (_orders.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: const BoxDecoration(
                  color: Color(0xFFE8F5E9),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.local_shipping_outlined, size: 48, color: Color(0xFF2E7D32)),
              ),
              const SizedBox(height: 16),
              const Text(
                'No Hardware Orders Yet',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Color(0xFF1B5E20)),
              ),
              const SizedBox(height: 8),
              const Text(
                'Order sensors, climate controllers, and IoT gateways to equip your rearing shed.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12.5, color: Colors.grey),
              ),
              const SizedBox(height: 20),
              if (widget.onBrowseProducts != null)
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF2E7D32),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 11),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: widget.onBrowseProducts,
                  icon: const Icon(Icons.storefront_outlined, size: 18),
                  label: const Text('Explore Hardware Store', style: TextStyle(fontWeight: FontWeight.w700)),
                ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _fetchOrders,
      color: const Color(0xFF2E7D32),
      child: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: _orders.length,
        itemBuilder: (context, index) {
          final o = _orders[index];
          final orderId = o['id']?.toString() ?? 'ORD-${index + 1}';
          final status = (o['status']?.toString() ?? 'PENDING').toUpperCase();
          final statusCol = _statusColor(status);
          final items = (o['items'] as List?) ?? [];
          final totalMinor = (o['total_amount_minor_units'] as num?)?.toInt() ?? 0;
          final totalRs = totalMinor > 0 ? (totalMinor / 100).toStringAsFixed(0) : (o['total_amount']?.toString() ?? '0');
          final address = o['shipping_address']?.toString() ?? 'Farm Delivery';
          final dateStr = o['created_at']?.toString() ?? '';
          final dateFormatted = dateStr.isNotEmpty ? dateStr.split('T').first : 'Recent';

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
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.local_shipping_outlined, color: Color(0xFF2E7D32), size: 18),
                          const SizedBox(width: 6),
                          Text(
                            orderId,
                            style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: Color(0xFF1B5E20)),
                          ),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: statusCol.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: statusCol.withValues(alpha: 0.3)),
                        ),
                        child: Text(
                          status,
                          style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: statusCol),
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 18),

                  // Order items list
                  if (items.isNotEmpty) ...[
                    ...items.map((item) {
                      final name = item['product_name'] ?? item['name'] ?? 'Hardware Item';
                      final qty = item['quantity'] ?? 1;
                      final unitPrice = (item['price_minor_units'] as num?) != null
                          ? ((item['price_minor_units'] as num) / 100).toStringAsFixed(0)
                          : '';
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 2),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('• $name x $qty', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                            if (unitPrice.isNotEmpty)
                              Text('₹$unitPrice', style: TextStyle(fontSize: 11.5, color: Colors.grey.shade700)),
                          ],
                        ),
                      );
                    }),
                    const SizedBox(height: 8),
                  ],

                  // Shipping destination & date
                  Row(
                    children: [
                      Icon(Icons.location_on_outlined, size: 13, color: Colors.grey.shade600),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          address,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                        ),
                      ),
                      Text(dateFormatted, style: TextStyle(fontSize: 10.5, color: Colors.grey.shade500)),
                    ],
                  ),
                  const SizedBox(height: 10),

                  // Total amount row
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Total Amount:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey)),
                      Text(
                        '₹$totalRs',
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: Color(0xFF1B5E20)),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
