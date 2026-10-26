import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_failure.dart';
import '../../l10n/app_localizations.dart';
import 'auth_repository.dart';
import 'providers.dart';

class AccountPage extends ConsumerStatefulWidget {
  const AccountPage({super.key});
  @override
  ConsumerState<AccountPage> createState() => _AccountPageState();
}

class _AccountPageState extends ConsumerState<AccountPage> {
  final form = GlobalKey<FormState>();
  final email = TextEditingController();
  final password = TextEditingController();
  final name = TextEditingController();
  final token = TextEditingController();
  String mode = 'login';
  String? message;
  bool busy = false;
  List<DeviceSession> devices = [];
  int devicesEpoch = -1;
  String? devicesOwner;

  @override
  void initState() {
    super.initState();
    Future.microtask(
      () => run(() async {
        await ref.read(sessionProvider.notifier).restore();
        await loadDevices();
      }),
    );
  }

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    name.dispose();
    token.dispose();
    super.dispose();
  }

  Future<void> loadDevices() async {
    final session = ref.read(sessionStateProvider);
    if (session.profile == null) {
      devices = [];
      devicesEpoch = -1;
      devicesOwner = null;
      return;
    }
    final result = await ref.read(authRepositoryProvider).sessions();
    if (!mounted) return;
    final current = ref.read(sessionStateProvider);
    if (current.generation != session.generation ||
        current.profile?.id != session.profile!.id) {
      return;
    }
    devices = result;
    devicesEpoch = session.generation;
    devicesOwner = session.profile!.id;
  }

  Future<void> run(
    Future<void> Function() action, {
    bool signingOut = false,
  }) async {
    if (!mounted) return;
    setState(() {
      busy = true;
      message = null;
    });
    try {
      await action();
    } catch (error) {
      if (!mounted) return;
      final text = AppLocalizations.of(context)!;
      final code = error is ApiFailure ? error.code : '';
      if (code == 'invalid_session') {
        ref.read(sessionProvider.notifier).invalidate();
      }
      message = signingOut
          ? text.authLogoutUnconfirmed
          : switch (code) {
              'invalid_credentials' => text.authInvalid,
              'rate_limited' => text.authLimited,
              'invalid_session' => text.authSessionExpired,
              'delivery_unavailable' ||
              'service_unavailable' => text.authUnavailable,
              _ => text.authError,
            };
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> submit() async {
    if (!form.currentState!.validate()) return;
    await run(() async {
      final text = AppLocalizations.of(context)!;
      if (mode == 'login') {
        await ref
            .read(sessionProvider.notifier)
            .login(email.text.trim(), password.text);
        password.clear();
        await loadDevices();
      } else {
        final data = <String, dynamic>{};
        if (!{'verify', 'reset'}.contains(mode)) {
          data['email'] = email.text.trim();
        }
        if ({'register', 'reset'}.contains(mode)) {
          data['password'] = password.text;
        }
        if ({'verify', 'reset'}.contains(mode)) {
          data['token'] = token.text.trim();
        }
        if (mode == 'register') {
          data['display_name'] = name.text.trim();
          data['locale'] = Localizations.localeOf(context).languageCode;
        }
        await ref.read(authRepositoryProvider).command(mode, data);
        password.clear();
        token.clear();
        message =
            {'register', 'request-reset', 'request-verification'}.contains(mode)
            ? text.authAccepted
            : text.authCompleted;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final text = AppLocalizations.of(context)!;
    final session = ref.watch(sessionStateProvider);
    final user = session.profile;
    final loadedDevices =
        user != null &&
        devicesOwner == user.id &&
        devicesEpoch == session.generation;
    final visibleDevices = loadedDevices ? devices : const <DeviceSession>[];
    final modes = {
      'login': text.authLogin,
      'register': text.authRegister,
      'request-verification': text.authRequestVerification,
      'verify': text.authVerify,
      'request-reset': text.authRequestReset,
      'reset': text.authReset,
    };
    return Scaffold(
      appBar: AppBar(title: Text(text.authTitle)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            if (busy || session.status == SessionStatus.restoring)
              Semantics(
                label: text.authLoading,
                child: const LinearProgressIndicator(),
              ),
            if (session.status == SessionStatus.unavailable) ...[
              Text(text.mobileSessionUnavailable),
              TextButton(
                onPressed: busy
                    ? null
                    : () => run(() async {
                        await ref
                            .read(sessionStateProvider.notifier)
                            .retryRestore();
                        await loadDevices();
                      }),
                child: Text(text.cmsRetry),
              ),
            ],
            if (message != null)
              Semantics(
                liveRegion: true,
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  child: Text(message!),
                ),
              ),
            if (user != null) ...[
              Text(user.name, style: Theme.of(context).textTheme.headlineSmall),
              TextButton(
                onPressed: busy
                    ? null
                    : () => run(() async {
                        await ref.read(sessionProvider.notifier).logout();
                        devices = [];
                      }, signingOut: true),
                child: Text(text.authLogout),
              ),
              TextButton(
                onPressed: busy
                    ? null
                    : () => run(() async {
                        await ref
                            .read(sessionProvider.notifier)
                            .logout(all: true);
                        devices = [];
                      }, signingOut: true),
                child: Text(text.authLogoutAll),
              ),
              Text(
                text.authSessions,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              if (loadedDevices && visibleDevices.isEmpty)
                Text(text.authNoSessions),
              if (!loadedDevices && !busy)
                TextButton(
                  onPressed: () => run(loadDevices),
                  child: Text(text.cmsRetry),
                ),
              for (final device in visibleDevices)
                ListTile(
                  title: Text(device.name),
                  subtitle: device.current ? Text(text.authCurrent) : null,
                  trailing: TextButton(
                    onPressed: busy
                        ? null
                        : () => run(() async {
                            if (device.current) {
                              await ref.read(sessionProvider.notifier).logout();
                              devices = [];
                            } else {
                              await ref
                                  .read(authRepositoryProvider)
                                  .revoke(device.id);
                              await loadDevices();
                            }
                          }, signingOut: device.current),
                    child: Text(text.authRevoke),
                  ),
                ),
            ] else
              Form(
                key: form,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    DropdownButtonFormField<String>(
                      initialValue: mode,
                      isExpanded: true,
                      decoration: InputDecoration(labelText: text.authTitle),
                      items: modes.entries
                          .map(
                            (entry) => DropdownMenuItem(
                              value: entry.key,
                              child: Text(entry.value),
                            ),
                          )
                          .toList(),
                      onChanged: busy
                          ? null
                          : (value) => setState(() {
                              mode = value!;
                              message = null;
                              password.clear();
                              token.clear();
                            }),
                    ),
                    if (mode == 'register')
                      TextFormField(
                        controller: name,
                        decoration: InputDecoration(labelText: text.authName),
                        maxLength: 120,
                        validator: (value) =>
                            value == null || value.trim().isEmpty
                            ? text.authError
                            : null,
                      ),
                    if (!{'verify', 'reset'}.contains(mode))
                      TextFormField(
                        controller: email,
                        keyboardType: TextInputType.emailAddress,
                        autofillHints: const [AutofillHints.email],
                        decoration: InputDecoration(labelText: text.authEmail),
                        maxLength: 254,
                        validator: (value) =>
                            value == null || !value.contains('@')
                            ? text.authError
                            : null,
                      ),
                    if ({'verify', 'reset'}.contains(mode))
                      TextFormField(
                        controller: token,
                        decoration: InputDecoration(labelText: text.authToken),
                        maxLength: 256,
                        validator: (value) => value == null || value.length < 32
                            ? text.authError
                            : null,
                      ),
                    if ({'login', 'register', 'reset'}.contains(mode))
                      TextFormField(
                        controller: password,
                        obscureText: true,
                        enableSuggestions: false,
                        autocorrect: false,
                        autofillHints: [
                          mode == 'login'
                              ? AutofillHints.password
                              : AutofillHints.newPassword,
                        ],
                        decoration: InputDecoration(
                          labelText: text.authPassword,
                          helperText: text.authPasswordHelp,
                        ),
                        maxLength: 128,
                        validator: (value) => value == null || value.length < 12
                            ? text.authPasswordHelp
                            : null,
                      ),
                    const SizedBox(height: 20),
                    FilledButton(
                      onPressed: busy ? null : submit,
                      child: Text(busy ? text.authLoading : modes[mode]!),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
