import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/sericare_provider.dart';

class UserProfileModal extends StatefulWidget {
  const UserProfileModal({Key? key}) : super(key: key);

  @override
  State<UserProfileModal> createState() => _UserProfileModalState();
}

class _UserProfileModalState extends State<UserProfileModal> {
  late TextEditingController _nameController;
  late TextEditingController _phoneController;
  late TextEditingController _batchController;
  late TextEditingController _capacityController;
  bool _isEditing = false;

  @override
  void initState() {
    super.initState();
    final provider = Provider.of<SeriCareProvider>(context, listen: false);
    _nameController = TextEditingController(text: provider.userName);
    _phoneController = TextEditingController(text: provider.userPhone);
    _batchController = TextEditingController(text: provider.batchId);
    _capacityController = TextEditingController(text: provider.dflCapacity);
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _batchController.dispose();
    _capacityController.dispose();
    super.dispose();
  }

  void _saveProfile(SeriCareProvider provider) {
    provider.updateUserProfile(
      name: _nameController.text.trim(),
      phone: _phoneController.text.trim(),
      batch: _batchController.text.trim(),
      capacity: _capacityController.text.trim(),
    );
    setState(() => _isEditing = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('User Profile updated successfully'),
        backgroundColor: Color(0xFF2E7D32),
        duration: Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SeriCareProvider>(context);

    return Container(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Handle Bar
            Center(
              child: Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: const Color(0xFFCFD8DC),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 14),

            // Header Row
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Row(
                  children: [
                    Text('👤 ', style: TextStyle(fontSize: 20)),
                    Text(
                      'Farmer Profile',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w800,
                        color: Color(0xFF1B5E20),
                      ),
                    ),
                  ],
                ),
                Row(
                  children: [
                    TextButton.icon(
                      style: TextButton.styleFrom(
                        foregroundColor: const Color(0xFF2E7D32),
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      ),
                      icon: Icon(_isEditing ? Icons.check : Icons.edit_note, size: 18),
                      label: Text(_isEditing ? 'Save' : 'Edit'),
                      onPressed: () {
                        if (_isEditing) {
                          _saveProfile(provider);
                        } else {
                          setState(() => _isEditing = true);
                        }
                      },
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, size: 20),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),

            // User Avatar Banner Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFFE8F5E9), Color(0xFFC8E6C9)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 28,
                    backgroundColor: const Color(0xFF2E7D32),
                    child: Text(
                      provider.userName.isNotEmpty ? provider.userName[0].toUpperCase() : 'R',
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          provider.userName,
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF1B5E20),
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${provider.region} · ${provider.experience}',
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF388E3C),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFF1B5E20),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            'Active Batch: ${provider.batchId}',
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Form / Data Fields
            if (_isEditing) ...[
              _buildTextField('Farmer Name', _nameController, Icons.person),
              const SizedBox(height: 10),
              _buildTextField('Phone Number', _phoneController, Icons.phone, keyboardType: TextInputType.phone),
              const SizedBox(height: 10),
              _buildTextField('Batch ID', _batchController, Icons.tag),
              const SizedBox(height: 10),
              _buildTextField('Shed Capacity (DFLs)', _capacityController, Icons.grid_view, keyboardType: TextInputType.number),
              const SizedBox(height: 14),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF2E7D32),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () => _saveProfile(provider),
                child: const Text('Save Profile Changes', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ] else ...[
              _buildInfoRow('Phone Number', provider.userPhone),
              _buildInfoRow('Registered Shed', '${provider.shedData.shedId.toUpperCase()} (${provider.shedData.farmName})'),
              _buildInfoRow('Cluster Region', provider.region),
              _buildInfoRow('Silkworm Breed', provider.breed),
              _buildInfoRow('Rearing Capacity', provider.dflCapacity.contains('DFL') ? provider.dflCapacity : '${provider.dflCapacity} DFL'),
              _buildInfoRow('Rearing Stage', '${provider.currentGrowthStage}rd Instar (FC1 x FC2)'),
              _buildLanguageRow(context, provider),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTextField(String label, TextEditingController controller, IconData icon, {TextInputType? keyboardType}) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon, size: 20, color: const Color(0xFF2E7D32)),
        isDense: true,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
        ),
      ),
    );
  }

  Widget _buildLanguageRow(BuildContext context, SeriCareProvider provider) {
    String currentLangName;
    if (provider.locale.languageCode == 'kn') {
      currentLangName = 'ಕನ್ನಡ';
    } else if (provider.locale.languageCode == 'te') {
      currentLangName = 'తెలుగు';
    } else {
      currentLangName = 'English';
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: () => _showLanguageSelector(context, provider),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFFF9FBF8),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFFC8E6C9), width: 1.2),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const Flexible(
                  flex: 5,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text('🌐 ', style: TextStyle(fontSize: 13)),
                      Flexible(
                        child: Text(
                          'App Language',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(fontSize: 12, color: Color(0xFF5A695C), fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Flexible(
                  flex: 6,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE8F5E9),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          currentLangName,
                          style: const TextStyle(fontSize: 12, color: Color(0xFF1B5E20), fontWeight: FontWeight.w800),
                        ),
                      ),
                      const SizedBox(width: 4),
                      const Icon(Icons.arrow_drop_down, color: Color(0xFF2E7D32), size: 18),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _showLanguageSelector(BuildContext context, SeriCareProvider provider) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      backgroundColor: Colors.white,
      builder: (ctx) {
        final currentCode = provider.locale.languageCode;
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Select Language / ಭಾಷೆ ಆಯ್ಕೆ',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF1B5E20)),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, size: 20),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                ListTile(
                  leading: const Icon(Icons.language, color: Color(0xFF2E7D32)),
                  title: const Text('English', style: TextStyle(fontWeight: FontWeight.w700)),
                  trailing: currentCode == 'en' ? const Icon(Icons.check_circle, color: Color(0xFF2E7D32)) : null,
                  onTap: () {
                    provider.setLocale(const Locale('en'));
                    Navigator.pop(ctx);
                    if (mounted) setState(() {});
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.language, color: Color(0xFF2E7D32)),
                  title: const Text('ಕನ್ನಡ (Kannada)', style: TextStyle(fontWeight: FontWeight.w700)),
                  trailing: currentCode == 'kn' ? const Icon(Icons.check_circle, color: Color(0xFF2E7D32)) : null,
                  onTap: () {
                    provider.setLocale(const Locale('kn'));
                    Navigator.pop(ctx);
                    if (mounted) setState(() {});
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.language, color: Color(0xFF2E7D32)),
                  title: const Text('తెలుగు (Telugu)', style: TextStyle(fontWeight: FontWeight.w700)),
                  trailing: currentCode == 'te' ? const Icon(Icons.check_circle, color: Color(0xFF2E7D32)) : null,
                  onTap: () {
                    provider.setLocale(const Locale('te'));
                    Navigator.pop(ctx);
                    if (mounted) setState(() {});
                  },
                ),
                const SizedBox(height: 8),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: const Color(0xFFF9FBF8),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: const Color(0xFFE8EFE5)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Flexible(
              flex: 5,
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12, color: Color(0xFF5A695C), fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(width: 8),
            Flexible(
              flex: 6,
              child: Align(
                alignment: Alignment.centerRight,
                child: Text(
                  value,
                  textAlign: TextAlign.end,
                  overflow: TextOverflow.ellipsis,
                  maxLines: 2,
                  style: const TextStyle(fontSize: 12, color: Color(0xFF1C251D), fontWeight: FontWeight.w700),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
