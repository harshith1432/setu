import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/setu_provider.dart';

class AuthScreen extends StatefulWidget {
  final VoidCallback onLoginSuccess;

  const AuthScreen({Key? key, required this.onLoginSuccess}) : super(key: key);

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  bool _isSignUp = false;
  bool _isLoading = false;
  bool _obscurePassword = true;

  // Controllers
  final _usernameController = TextEditingController(text: 'ramesh_farmer');
  final _passwordController = TextEditingController(text: 'setu2026');
  final _fullNameController = TextEditingController(text: 'Ramesh Gowda');
  final _phoneController = TextEditingController(text: '+91 98450 12345');
  final _farmNameController = TextEditingController(text: 'Green Valley Sericulture Farm');
  final _batchIdController = TextEditingController(text: 'SERI-2026-M04');
  final _dflController = TextEditingController(text: '200 DFL');

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    _fullNameController.dispose();
    _phoneController.dispose();
    _farmNameController.dispose();
    _batchIdController.dispose();
    _dflController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final provider = Provider.of<SetuProvider>(context, listen: false);
    final uname = _usernameController.text.trim();
    final pwd = _passwordController.text.trim();

    if (uname.isEmpty || pwd.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in username and password')),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      if (_isSignUp) {
        final result = await provider.register(
          uname: uname,
          pwd: pwd,
          fullName: _fullNameController.text.trim().isNotEmpty ? _fullNameController.text.trim() : 'Farmer $uname',
          phone: _phoneController.text.trim().isNotEmpty ? _phoneController.text.trim() : '+91 98450 00000',
          farmName: _farmNameController.text.trim().isNotEmpty ? _farmNameController.text.trim() : 'Seri Farm $uname',
          batchId: _batchIdController.text.trim().isNotEmpty ? _batchIdController.text.trim() : 'SERI-2026-B01',
          dflCapacity: _dflController.text.trim().isNotEmpty ? _dflController.text.trim() : '150 DFL',
        );
        if (mounted) {
          if (result.success) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                backgroundColor: const Color(0xFF2E7D32),
                content: Text(result.message ?? 'Farmer registered successfully!'),
              ),
            );
            widget.onLoginSuccess();
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                backgroundColor: const Color(0xFFC62828),
                content: Text(result.message ?? 'Registration failed. Please try again.'),
              ),
            );
          }
        }
      } else {
        final success = await provider.login(uname, pwd);
        if (mounted) {
          if (success) {
            widget.onLoginSuccess();
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                backgroundColor: Color(0xFFC62828),
                content: Text('Invalid username or password'),
              ),
            );
          }
        }
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _showLanguageSelector(BuildContext context, SetuProvider provider) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      backgroundColor: Colors.white,
      builder: (ctx) {
        final current = provider.locale.languageCode;
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
                  trailing: current == 'en' ? const Icon(Icons.check_circle, color: Color(0xFF2E7D32)) : null,
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
                  trailing: current == 'kn' ? const Icon(Icons.check_circle, color: Color(0xFF2E7D32)) : null,
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
                  trailing: current == 'te' ? const Icon(Icons.check_circle, color: Color(0xFF2E7D32)) : null,
                  onTap: () {
                    provider.setLocale(const Locale('te'));
                    Navigator.pop(ctx);
                    if (mounted) setState(() {});
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SetuProvider>(context);

    return Scaffold(
      backgroundColor: const Color(0xFFF5F7F2),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Language Selection Chip (Replaced IP/Port info)
                Align(
                  alignment: Alignment.topRight,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(20),
                    onTap: () => _showLanguageSelector(context, provider),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: const Color(0xFFE8F5E9),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: const Color(0xFFC8E6C9)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.language, size: 14, color: Color(0xFF2E7D32)),
                          const SizedBox(width: 4),
                          Text(
                            provider.locale.languageCode == 'kn'
                                ? 'ಕನ್ನಡ'
                                : (provider.locale.languageCode == 'te' ? 'తెలుగు' : 'English'),
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF2E7D32)),
                          ),
                          const Icon(Icons.arrow_drop_down, size: 16, color: Color(0xFF2E7D32)),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),

                // Brand Header
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFFC8E6C9), Color(0xFF81C784)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF4CAF50).withValues(alpha: 0.3),
                        blurRadius: 16,
                        offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Text('🐛', style: TextStyle(fontSize: 40)),
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  'Setu',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF1B5E20),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _isSignUp ? 'Create your Farmer Account' : 'Farmer Portal Login',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF5A695C),
                  ),
                ),
                const SizedBox(height: 20),

                // Card Container
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: const Color(0xFFE0E7DC)),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.04),
                        blurRadius: 14,
                        offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Username
                      TextField(
                        controller: _usernameController,
                        decoration: InputDecoration(
                          labelText: 'Username or Phone',
                          prefixIcon: const Icon(Icons.person_outline, color: Color(0xFF2E7D32)),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
                          ),
                          contentPadding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                        ),
                      ),
                      const SizedBox(height: 14),

                      // Password
                      TextField(
                        controller: _passwordController,
                        obscureText: _obscurePassword,
                        decoration: InputDecoration(
                          labelText: 'Password',
                          prefixIcon: const Icon(Icons.lock_outline, color: Color(0xFF2E7D32)),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscurePassword ? Icons.visibility_off : Icons.visibility,
                              color: const Color(0xFF5A695C),
                              size: 20,
                            ),
                            onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                          ),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
                          ),
                          contentPadding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                        ),
                      ),

                      // Extra Fields for Sign Up
                      if (_isSignUp) ...[
                        const SizedBox(height: 14),
                        TextField(
                          controller: _fullNameController,
                          decoration: InputDecoration(
                            labelText: 'Full Name',
                            prefixIcon: const Icon(Icons.badge_outlined, color: Color(0xFF2E7D32)),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                            contentPadding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                          ),
                        ),
                        const SizedBox(height: 14),
                        TextField(
                          controller: _phoneController,
                          keyboardType: TextInputType.phone,
                          decoration: InputDecoration(
                            labelText: 'Phone Number',
                            prefixIcon: const Icon(Icons.phone_outlined, color: Color(0xFF2E7D32)),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                            contentPadding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                          ),
                        ),
                        const SizedBox(height: 14),
                        TextField(
                          controller: _farmNameController,
                          decoration: InputDecoration(
                            labelText: 'Farm Name',
                            prefixIcon: const Text(' 🏠 ', style: TextStyle(fontSize: 16)),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                            contentPadding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                          ),
                        ),
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _batchIdController,
                                decoration: InputDecoration(
                                  labelText: 'Batch ID',
                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                                  contentPadding: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: TextField(
                                controller: _dflController,
                                decoration: InputDecoration(
                                  labelText: 'DFL Capacity',
                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                                  contentPadding: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                      const SizedBox(height: 20),

                      // Submit Button
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF2E7D32),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          elevation: 2,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                        ),
                        onPressed: _isLoading ? null : _submit,
                        child: _isLoading
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                              )
                            : Text(
                                _isSignUp ? 'Sign Up & Enroll Farm' : 'Log In & Open Shed',
                                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                              ),
                      ),
                      const SizedBox(height: 14),

                      // Toggle between Login & Sign Up
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            _isSignUp ? 'Already enrolled? ' : 'New farmer? ',
                            style: const TextStyle(fontSize: 13, color: Color(0xFF5A695C)),
                          ),
                          GestureDetector(
                            onTap: () {
                              setState(() {
                                _isSignUp = !_isSignUp;
                                if (_isSignUp) {
                                  // Clear demo defaults when entering Sign Up mode
                                  if (_usernameController.text == 'ramesh_farmer') _usernameController.clear();
                                  if (_passwordController.text == 'setu2026') _passwordController.clear();
                                  if (_fullNameController.text == 'Ramesh Gowda') _fullNameController.clear();
                                  if (_phoneController.text == '+91 98450 12345') _phoneController.clear();
                                }
                              });
                            },
                            child: Text(
                              _isSignUp ? 'Log In here' : 'Sign Up now',
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF1B5E20),
                              ),
                            ),
                          ),
                        ],
                      ),
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
}
