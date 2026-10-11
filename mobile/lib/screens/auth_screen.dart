import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/setu_provider.dart';

class AuthScreen extends StatefulWidget {
  final VoidCallback onLoginSuccess;

  const AuthScreen({super.key, required this.onLoginSuccess});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

enum LoginMethod { otp, password }

class _AuthScreenState extends State<AuthScreen> {
  bool _isSignUp = true; // Show Create Account first
  LoginMethod _loginMethod = LoginMethod.otp;
  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _isOtpSent = false;

  // Controllers
  final _usernameController = TextEditingController(text: 'ramesh_farmer');
  final _passwordController = TextEditingController(text: 'setu2026');
  final _fullNameController = TextEditingController(text: 'Ramesh Gowda');
  final _phoneController = TextEditingController(text: '+91 98450 12345');
  final _otpController = TextEditingController();
  final _farmNameController = TextEditingController(text: 'Green Valley Sericulture Farm');
  final _batchIdController = TextEditingController(text: 'SERI-2026-M04');
  final _dflController = TextEditingController(text: '200 DFL');

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    _fullNameController.dispose();
    _phoneController.dispose();
    _otpController.dispose();
    _farmNameController.dispose();
    _batchIdController.dispose();
    _dflController.dispose();
    super.dispose();
  }

  Future<void> _startPhoneAuth() async {
    final provider = Provider.of<SetuProvider>(context, listen: false);
    final phone = _phoneController.text.trim();
    if (phone.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter your phone number with country code.')),
      );
      return;
    }

    setState(() => _isLoading = true);
    try {
      final result = await provider.startPhoneAuthentication(phone);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result.message),
          backgroundColor: result.success ? const Color(0xFF2E7D32) : const Color(0xFFC62828),
        ),
      );
      if (result.success && result.codeSent) {
        setState(() => _isOtpSent = true);
      } else if (result.success) {
        widget.onLoginSuccess();
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _verifyOtp() async {
    final provider = Provider.of<SetuProvider>(context, listen: false);
    final code = _otpController.text.trim();
    if (code.length < 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter the 6-digit OTP.')),
      );
      return;
    }

    setState(() => _isLoading = true);
    try {
      final result = await provider.signInWithPhoneCode(
        code: code,
        preferredName: _fullNameController.text.trim(),
        preferredPhone: _phoneController.text.trim(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result.message),
          backgroundColor: result.success ? const Color(0xFF2E7D32) : const Color(0xFFC62828),
        ),
      );
      if (result.success) {
        widget.onLoginSuccess();
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _signInWithGoogle() async {
    final provider = Provider.of<SetuProvider>(context, listen: false);
    setState(() => _isLoading = true);
    try {
      final result = await provider.signInWithGoogle();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result.message),
          backgroundColor: result.success ? const Color(0xFF2E7D32) : const Color(0xFFC62828),
        ),
      );
      if (result.success) {
        widget.onLoginSuccess();
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _submit() async {
    final provider = Provider.of<SetuProvider>(context, listen: false);
    final uname = _usernameController.text.trim();
    final pwd = _passwordController.text.trim();

    setState(() => _isLoading = true);

    try {
      if (_isSignUp) {
        final phone = _phoneController.text.trim();
        final finalUname = uname.isNotEmpty
            ? uname
            : (phone.isNotEmpty ? phone.replaceAll(RegExp(r'\s+'), '') : 'farmer_${DateTime.now().millisecondsSinceEpoch % 10000}');

        if (pwd.isEmpty) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Please enter a password.')),
          );
          return;
        }

        final result = await provider.register(
          uname: finalUname,
          pwd: pwd,
          fullName: _fullNameController.text.trim().isNotEmpty ? _fullNameController.text.trim() : 'Farmer $finalUname',
          phone: phone.isNotEmpty ? phone : '+91 98450 00000',
          farmName: _farmNameController.text.trim().isNotEmpty ? _farmNameController.text.trim() : 'Seri Farm',
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
        if (uname.isEmpty || pwd.isEmpty) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Please fill in username and password')),
          );
          return;
        }
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

  void _showLoginMethodSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      backgroundColor: Colors.white,
      builder: (ctx) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Center(
                  child: Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                const Text(
                  'Choose Login Method',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF1B5E20),
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Select how you would like to sign in to your account:',
                  style: TextStyle(fontSize: 12.5, color: Color(0xFF5A695C)),
                ),
                const SizedBox(height: 18),
                ListTile(
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                    side: const BorderSide(color: Color(0xFFE0E7DC)),
                  ),
                  tileColor: const Color(0xFFF9FBF8),
                  leading: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE8F5E9),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.sms_rounded, color: Color(0xFF2E7D32)),
                  ),
                  title: const Text(
                    'Login with Mobile OTP',
                    style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                  ),
                  subtitle: const Text(
                    'Quick sign-in using one-time SMS code',
                    style: TextStyle(fontSize: 12, color: Color(0xFF5A695C)),
                  ),
                  trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 16, color: Color(0xFF2E7D32)),
                  onTap: () {
                    Navigator.pop(ctx);
                    setState(() {
                      _isSignUp = false;
                      _loginMethod = LoginMethod.otp;
                      _isOtpSent = false;
                      _otpController.clear();
                    });
                  },
                ),
                const SizedBox(height: 12),
                ListTile(
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                    side: const BorderSide(color: Color(0xFFE0E7DC)),
                  ),
                  tileColor: const Color(0xFFF9FBF8),
                  leading: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE8F5E9),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.lock_outline_rounded, color: Color(0xFF2E7D32)),
                  ),
                  title: const Text(
                    'Login with Password',
                    style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
                  ),
                  subtitle: const Text(
                    'Sign in using your Username or Phone & Password',
                    style: TextStyle(fontSize: 12, color: Color(0xFF5A695C)),
                  ),
                  trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 16, color: Color(0xFF2E7D32)),
                  onTap: () {
                    Navigator.pop(ctx);
                    setState(() {
                      _isSignUp = false;
                      _loginMethod = LoginMethod.password;
                    });
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
                // Language Selection Chip
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
                const SizedBox(height: 8),

                // Brand Header
                SizedBox(
                  width: 90,
                  height: 90,
                  child: Image.asset(
                    'assets/images/app_logo.png',
                    width: 90,
                    height: 90,
                    fit: BoxFit.contain,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  _isSignUp
                      ? 'Create Farmer Account'
                      : (_loginMethod == LoginMethod.otp ? 'Farmer Login (OTP)' : 'Farmer Login'),
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF1B5E20),
                    letterSpacing: 0.3,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  _isSignUp
                      ? 'Register your shed to start automated monitoring'
                      : (_loginMethod == LoginMethod.otp
                          ? 'Sign in using one-time SMS verification'
                          : 'Sign in using your password credentials'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF5A695C),
                  ),
                ),
                const SizedBox(height: 18),

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
                        blurRadius: 16,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // IF CREATE ACCOUNT (shown first)
                      if (_isSignUp) ...[
                        TextField(
                          controller: _fullNameController,
                          decoration: InputDecoration(
                            labelText: 'Full Name',
                            hintText: 'e.g. Ramesh Gowda',
                            prefixIcon: const Icon(Icons.person_outline, color: Color(0xFF2E7D32)),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                              borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
                            ),
                            contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                          ),
                        ),
                        const SizedBox(height: 14),
                        TextField(
                          controller: _phoneController,
                          keyboardType: TextInputType.phone,
                          decoration: InputDecoration(
                            labelText: 'Mobile Number',
                            hintText: '+91 98450 12345',
                            prefixIcon: const Icon(Icons.phone_android_rounded, color: Color(0xFF2E7D32)),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                              borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
                            ),
                            contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                          ),
                        ),
                        const SizedBox(height: 14),
                        TextField(
                          controller: _passwordController,
                          obscureText: _obscurePassword,
                          decoration: InputDecoration(
                            labelText: 'Create Password',
                            prefixIcon: const Icon(Icons.lock_outline, color: Color(0xFF2E7D32)),
                            suffixIcon: IconButton(
                              icon: Icon(
                                _obscurePassword ? Icons.visibility_off : Icons.visibility,
                                color: const Color(0xFF5A695C),
                                size: 20,
                              ),
                              onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                            ),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                              borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
                            ),
                            contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                          ),
                        ),
                        const SizedBox(height: 14),
                        TextField(
                          controller: _farmNameController,
                          decoration: InputDecoration(
                            labelText: 'Farm Name / Shed ID',
                            hintText: 'e.g. Green Valley Farm Shed 1',
                            prefixIcon: const Icon(Icons.roofing_rounded, color: Color(0xFF2E7D32)),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                              borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
                            ),
                            contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
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
                                  hintText: 'SERI-2026-B01',
                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                                  contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: TextField(
                                controller: _dflController,
                                decoration: InputDecoration(
                                  labelText: 'DFL Capacity',
                                  hintText: '200 DFL',
                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                                  contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 18),
                        ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF2E7D32),
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            elevation: 1,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                          ),
                          onPressed: _isLoading ? null : _submit,
                          child: _isLoading
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                )
                              : const Text(
                                  'Create Account & Register Farm',
                                  style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w700),
                                ),
                        ),
                        const SizedBox(height: 16),
                        // Downside link to show login options
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Text(
                              'Already have an account? ',
                              style: TextStyle(fontSize: 13, color: Color(0xFF5A695C)),
                            ),
                            GestureDetector(
                              onTap: () => _showLoginMethodSheet(context),
                              child: const Text(
                                'Log In',
                                style: TextStyle(
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF1B5E20),
                                  decoration: TextDecoration.underline,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],

                      // IF LOGIN MODE (User chose to log in)
                      if (!_isSignUp) ...[
                        // Login with OTP fields
                        if (_loginMethod == LoginMethod.otp) ...[
                          TextField(
                            controller: _phoneController,
                            keyboardType: TextInputType.phone,
                            decoration: InputDecoration(
                              labelText: 'Mobile Number',
                              hintText: '+91 98450 12345',
                              prefixIcon: const Icon(Icons.phone_android_rounded, color: Color(0xFF2E7D32)),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(14),
                                borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
                              ),
                              contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                            ),
                          ),
                          if (_isOtpSent) ...[
                            const SizedBox(height: 12),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                              decoration: BoxDecoration(
                                color: const Color(0xFFE8F5E9),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.check_circle_rounded, color: Color(0xFF2E7D32), size: 16),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      'OTP sent to ${_phoneController.text}',
                                      style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600, color: Color(0xFF1B5E20)),
                                    ),
                                  ),
                                  GestureDetector(
                                    onTap: () => setState(() => _isOtpSent = false),
                                    child: const Text('Edit', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: Color(0xFF2E7D32))),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 12),
                            TextField(
                              controller: _otpController,
                              keyboardType: TextInputType.number,
                              decoration: InputDecoration(
                                labelText: 'Enter 6-Digit OTP',
                                prefixIcon: const Icon(Icons.sms_rounded, color: Color(0xFF2E7D32)),
                                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                                focusedBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(14),
                                  borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
                                ),
                                contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                              ),
                            ),
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Expanded(
                                  child: OutlinedButton(
                                    style: OutlinedButton.styleFrom(
                                      foregroundColor: const Color(0xFF2E7D32),
                                      side: const BorderSide(color: Color(0xFF2E7D32)),
                                      padding: const EdgeInsets.symmetric(vertical: 13),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                    ),
                                    onPressed: _isLoading ? null : _startPhoneAuth,
                                    child: const Text('Resend Code', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  flex: 2,
                                  child: ElevatedButton.icon(
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: const Color(0xFF2E7D32),
                                      foregroundColor: Colors.white,
                                      padding: const EdgeInsets.symmetric(vertical: 13),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                      elevation: 1,
                                    ),
                                    onPressed: _isLoading ? null : _verifyOtp,
                                    icon: const Icon(Icons.check_rounded, size: 18),
                                    label: _isLoading
                                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                        : const Text('Verify & Log In', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
                                  ),
                                ),
                              ],
                            ),
                          ] else ...[
                            const SizedBox(height: 16),
                            ElevatedButton.icon(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF2E7D32),
                                foregroundColor: Colors.white,
                                padding: const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                elevation: 1,
                              ),
                              onPressed: _isLoading ? null : _startPhoneAuth,
                              icon: const Icon(Icons.send_rounded, size: 18),
                              label: _isLoading
                                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                  : const Text('Send Verification OTP', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                            ),
                          ],
                        ],

                        // Login with Password fields
                        if (_loginMethod == LoginMethod.password) ...[
                          TextField(
                            controller: _usernameController,
                            decoration: InputDecoration(
                              labelText: 'Username or Mobile Number',
                              prefixIcon: const Icon(Icons.person_outline, color: Color(0xFF2E7D32)),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(14),
                                borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
                              ),
                              contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                            ),
                          ),
                          const SizedBox(height: 14),
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
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(14),
                                borderSide: const BorderSide(color: Color(0xFF2E7D32), width: 2),
                              ),
                              contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                            ),
                          ),
                          const SizedBox(height: 18),
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF2E7D32),
                              foregroundColor: Colors.white,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              elevation: 1,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                            ),
                            onPressed: _isLoading ? null : _submit,
                            child: _isLoading
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                  )
                                : const Text(
                                    'Log In & Access Shed',
                                    style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w700),
                                  ),
                          ),
                        ],

                        const SizedBox(height: 12),
                        // Switch between OTP and Password login
                        Center(
                          child: TextButton.icon(
                            style: TextButton.styleFrom(
                              foregroundColor: const Color(0xFF2E7D32),
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            ),
                            onPressed: () {
                              setState(() {
                                _loginMethod = _loginMethod == LoginMethod.otp
                                    ? LoginMethod.password
                                    : LoginMethod.otp;
                                _isOtpSent = false;
                                _otpController.clear();
                              });
                            },
                            icon: Icon(
                              _loginMethod == LoginMethod.otp
                                  ? Icons.lock_outline_rounded
                                  : Icons.sms_rounded,
                              size: 16,
                              color: const Color(0xFF2E7D32),
                            ),
                            label: Text(
                              _loginMethod == LoginMethod.otp
                                  ? 'Login with Password instead'
                                  : 'Login with Mobile OTP instead',
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: Color(0xFF2E7D32),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 6),
                        // Link back to Create Account
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Text(
                              'New farmer? ',
                              style: TextStyle(fontSize: 13, color: Color(0xFF5A695C)),
                            ),
                            GestureDetector(
                              onTap: () {
                                setState(() {
                                  _isSignUp = true;
                                  _isOtpSent = false;
                                  _otpController.clear();
                                });
                              },
                              child: const Text(
                                'Create an account',
                                style: TextStyle(
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFF1B5E20),
                                  decoration: TextDecoration.underline,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],

                      // Google Sign In & Divider
                      const SizedBox(height: 18),
                      Row(
                        children: [
                          const Expanded(child: Divider(color: Color(0xFFE2E8F0))),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                            child: Text(
                              'OR',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                color: Colors.grey.shade500,
                                letterSpacing: 1.2,
                              ),
                            ),
                          ),
                          const Expanded(child: Divider(color: Color(0xFFE2E8F0))),
                        ],
                      ),
                      const SizedBox(height: 14),
                      OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          backgroundColor: Colors.white,
                          foregroundColor: const Color(0xFF2C3E50),
                          side: const BorderSide(color: Color(0xFFE2E8F0)),
                          padding: const EdgeInsets.symmetric(vertical: 13),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                          elevation: 0,
                        ),
                        onPressed: _isLoading ? null : _signInWithGoogle,
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.account_circle_outlined, color: Color(0xFF4285F4), size: 20),
                            SizedBox(width: 8),
                            Text(
                              'Continue with Google',
                              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
                            ),
                          ],
                        ),
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
