import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_failure.dart';
import '../../core/api/domain_api.dart';
import '../../core/files/file_transport.dart';
import '../identity/providers.dart';
import 'helpdesk_files.dart';
import 'support_common.dart';

const ticketCategories = [
  'funding',
  'registration',
  'tax_compliance',
  'marketing',
  'technology',
  'business_planning',
  'banking',
  'mentoring',
  'general',
];
const ticketPriorities = ['low', 'normal', 'high'];

class OwnerTicket {
  final String id, number, category, subject, status, priority;
  final int version;
  OwnerTicket.fromJson(Map<String, dynamic> d)
    : id = identifier(d['id']),
      number = d['number'] as String,
      category = d['category'] as String,
      subject = d['subject'] as String,
      status = d['status'] as String,
      priority = d['priority'] as String,
      version = versionOf(d['version']) {
    if (d['access'] != 'owner' ||
        !ticketCategories.contains(category) ||
        !{
          'open',
          'assigned',
          'in_progress',
          'waiting_for_user',
          'resolved',
          'closed',
        }.contains(status)) {
      throw const FormatException();
    }
  }
}

class LegacyAttachment {
  final String id, name;
  final int size;
  LegacyAttachment.fromJson(Map<String, dynamic> d)
    : id = identifier(d['id']),
      name = d['filename'] as String,
      size = d['size_bytes'] as int {
    if (size < 1 || size > 32768) throw const FormatException();
  }
}

class SharedMessage {
  final String id, body;
  final DateTime createdAt;
  final List<LegacyAttachment> attachments;
  final List<SupportFile> files;
  SharedMessage.fromJson(Map<String, dynamic> d)
    : id = identifier(d['id']),
      body = d['body'] as String,
      createdAt = DateTime.parse(d['created_at'] as String),
      attachments = rows(d['attachments'], LegacyAttachment.fromJson, max: 3),
      files = rows(d['files'] ?? [], SupportFile.fromJson, max: 100) {
    if (d['internal'] != false) throw const FormatException('Private message');
  }
}

class TicketHistory {
  final String event, status;
  final String? reason;
  final int version;
  final DateTime createdAt;
  TicketHistory.fromJson(Map<String, dynamic> d)
    : event = d['event'] as String,
      status = d['status'] as String,
      reason = d['reason'] as String?,
      version = versionOf(d['version']),
      createdAt = DateTime.parse(d['created_at'] as String);
}

class SupportNotice {
  final String id, ticketId, event;
  final int version;
  final bool read;
  SupportNotice.fromJson(Map<String, dynamic> d)
    : id = identifier(d['id']),
      ticketId = identifier(d['ticket_id']),
      event = d['event'] as String,
      version = versionOf(d['version']),
      read = d['read_at'] != null;
}

class SupportPreference {
  final bool enabled;
  final int version;
  SupportPreference.fromJson(Map<String, dynamic> d)
    : enabled = d['enabled'] as bool,
      version = versionOf(d['version']);
}

bool validLegacyText(String content) =>
    utf8.encode(content).length <= 32768 &&
    content.isNotEmpty &&
    !RegExp(
      r'<\s*[!/?a-zA-Z]|javascript\s*:',
      caseSensitive: false,
    ).hasMatch(content) &&
    !content.runes.any(
      (r) => (r < 32 && ![9, 10, 13].contains(r)) || (r >= 127 && r <= 159),
    );
final helpdeskRepositoryProvider = Provider(
  (ref) => HelpdeskRepository(ref.watch(domainApiProvider)),
);
final helpdeskFilesRepositoryProvider = Provider(
  (ref) => HelpdeskFilesRepository(
    ref.watch(domainApiProvider),
    FileTransport(ref.watch(authRepositoryProvider)),
  ),
);

class HelpdeskRepository {
  final DomainApi api;
  HelpdeskRepository(this.api);
  String root(String org) => '/helpdesk/organizations/${identifier(org)}';
  String path(String org, String ticket) =>
      '${root(org)}/tickets/${identifier(ticket)}';
  OwnerTicket _ticket(Object? data, {String? expected, bool command = false}) =>
      decode(() {
        final ticket = OwnerTicket.fromJson(object(data));
        if (expected != null && ticket.id != expected) {
          throw const FormatException();
        }
        return ticket;
      }, command: command);
  Future<PageBatch<OwnerTicket>> list(
    String org, {
    String? cursor,
    String? status,
  }) async {
    final data = await api.get(
      '${root(org)}/tickets',
      queryParameters: {
        'queue': 'mine',
        'limit': 25,
        'cursor': ?cursor,
        'status': ?status,
      },
    );
    return decode(() => PageBatch.fromJson(object(data), OwnerTicket.fromJson));
  }

  Future<OwnerTicket> detail(String org, String ticket) async =>
      _ticket(await api.get(path(org, ticket)), expected: ticket);
  Future<OwnerTicket> create(String org, Map<String, Object> intent) async =>
      _ticket(
        await api.post('${root(org)}/tickets', data: intent),
        command: true,
      );
  Future<PageBatch<SharedMessage>> messages(
    String org,
    String ticket, {
    String? cursor,
  }) async {
    final data = await api.get(
      '${path(org, ticket)}/messages',
      queryParameters: {'limit': 25, 'cursor': ?cursor},
    );
    return decode(
      () => PageBatch.fromJson(object(data), SharedMessage.fromJson),
    );
  }

  Future<PageBatch<TicketHistory>> history(
    String org,
    String ticket, {
    String? cursor,
  }) async {
    final data = await api.get(
      '${path(org, ticket)}/history',
      queryParameters: {'limit': 25, 'cursor': ?cursor},
    );
    return decode(
      () => PageBatch.fromJson(object(data), TicketHistory.fromJson),
    );
  }

  Future<OwnerTicket> reply(
    String org,
    OwnerTicket ticket,
    String body, {
    List<String> fileIds = const [],
    String legacyText = '',
  }) async {
    if (body.trim().isEmpty ||
        body.length > 8000 ||
        (legacyText.isNotEmpty && !validLegacyText(legacyText)) ||
        fileIds.toSet().length != fileIds.length) {
      throw const ApiFailure(
        'invalid_request',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    final data = await api.post(
      '${path(org, ticket.id)}/messages',
      data: {
        'expected_version': ticket.version,
        'body': body,
        'internal': false,
        'file_ids': fileIds.map(identifier).toList(),
        'attachments': [
          if (legacyText.isNotEmpty)
            {'filename': 'attachment.txt', 'content': legacyText},
        ],
      },
    );
    return _ticket(data, expected: ticket.id, command: true);
  }

  Future<OwnerTicket> status(
    String org,
    OwnerTicket ticket,
    String reason, {
    required bool reopen,
  }) async {
    if (reason.trim().length < 3 ||
        reason.length > 500 ||
        (!reopen && ticket.status != 'resolved') ||
        (reopen && !{'resolved', 'closed'}.contains(ticket.status))) {
      throw const ApiFailure(
        'invalid_request',
        kind: ApiFailureKind.validation,
        outcome: CommandOutcome.notSent,
      );
    }
    final data = await api.post(
      '${path(org, ticket.id)}/${reopen ? 'reopen' : 'status'}',
      data: {
        'expected_version': ticket.version,
        'reason': reason,
        if (!reopen) 'status': 'closed',
      },
    );
    return _ticket(data, expected: ticket.id, command: true);
  }

  Future<PageBatch<SupportNotice>> notices(String org, {String? cursor}) async {
    final data = await api.get(
      '${root(org)}/notices',
      queryParameters: {'limit': 25, 'cursor': ?cursor},
    );
    return decode(
      () => PageBatch.fromJson(object(data), SupportNotice.fromJson),
    );
  }

  Future<void> readNotice(String org, SupportNotice notice) async {
    // Reauthorize the target before exposing a conversation from a notification.
    await detail(org, notice.ticketId);
    await api.post(
      '${root(org)}/notices/${notice.id}/read',
      data: {'expected_version': notice.version},
    );
  }

  Future<SupportPreference> preference(String org) async {
    final data = await api.get('${root(org)}/preference');
    return decode(() => SupportPreference.fromJson(object(data)));
  }

  Future<SupportPreference> setPreference(
    String org,
    SupportPreference current,
    bool enabled,
  ) async {
    final data = await api.post(
      '${root(org)}/preference',
      data: {'expected_version': current.version, 'enabled': enabled},
    );
    return decode(
      () => SupportPreference.fromJson(object(data)),
      command: true,
    );
  }

  Future<String> legacyDownload(
    String org,
    String ticket,
    LegacyAttachment attachment,
  ) async {
    final bytes = await api.requestBytes(
      '${path(org, ticket)}/attachments/${attachment.id}',
      maxBytes: 32768,
    );
    return decode(() {
      final text = utf8.decode(bytes);
      if (bytes.length != attachment.size || !validLegacyText(text)) {
        throw const FormatException();
      }
      return text;
    });
  }
}

class HelpdeskController extends ChangeNotifier with SupportRetry {
  final HelpdeskRepository repository;
  final String organizationId;
  List<OwnerTicket> tickets = [];
  List<SharedMessage> messages = [];
  List<TicketHistory> history = [];
  List<SupportNotice> notices = [];
  String? cursor, messageCursor, historyCursor, noticeCursor, statusFilter;
  OwnerTicket? ticket;
  SupportPreference? preference;
  String category = 'general',
      priority = 'normal',
      subject = '',
      body = '',
      reply = '',
      reason = '',
      legacyText = '';
  Map<String, Object>? creationIntent;
  String? uncertainScope;
  ApiFailure? failure;
  bool busy = false, requiresReadback = false, _disposed = false;
  int _generation = 0;
  HelpdeskController(this.repository, this.organizationId);
  bool get dirty =>
      subject.isNotEmpty ||
      body.isNotEmpty ||
      reply.isNotEmpty ||
      reason.isNotEmpty ||
      legacyText.isNotEmpty ||
      creationIntent != null;
  Future<void> list({bool more = false}) async {
    if (busy || retryDelayed || _disposed) return;
    busy = true;
    failure = null;
    notifyListeners();
    try {
      final result = await repository.list(
        organizationId,
        cursor: more ? cursor : null,
        status: statusFilter,
      );
      if (_disposed) return;
      tickets = more ? [...tickets, ...result.items] : result.items;
      cursor = result.cursor;
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e);
        recordFailure(failure!);
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<void> open(
    String id, {
    bool moreMessages = false,
    bool moreHistory = false,
  }) async {
    if (busy || retryDelayed || _disposed) return;
    final operation = ++_generation;
    final changed = ticket?.id != id;
    if (changed) {
      ticket = null;
      messages = [];
      history = [];
      reply = '';
      reason = '';
      legacyText = '';
      messageCursor = null;
      historyCursor = null;
    }
    busy = true;
    failure = null;
    notifyListeners();
    try {
      final current = await repository.detail(organizationId, id);
      final messageBatch = await repository.messages(
        organizationId,
        id,
        cursor: moreMessages ? messageCursor : null,
      );
      final historyBatch = await repository.history(
        organizationId,
        id,
        cursor: moreHistory ? historyCursor : null,
      );
      if (_disposed || operation != _generation) return;
      ticket = current;
      messages = moreMessages
          ? [...messages, ...messageBatch.items]
          : messageBatch.items;
      messageCursor = messageBatch.cursor;
      history = moreHistory
          ? [...history, ...historyBatch.items]
          : historyBatch.items;
      historyCursor = historyBatch.cursor;
      if (uncertainScope != 'preference' &&
          uncertainScope != 'notice' &&
          creationIntent == null) {
        requiresReadback = false;
        uncertainScope = null;
      }
    } catch (e) {
      if (!_disposed && operation == _generation) {
        failure = failureOf(e);
        recordFailure(failure!);
        requiresReadback = true;
        if (failure!.kind == ApiFailureKind.forbidden ||
            failure!.kind == ApiFailureKind.notFound) {
          ticket = null;
          messages = [];
          history = [];
        }
      }
    } finally {
      if (!_disposed && operation == _generation) {
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<void> create() async {
    if (busy || retryDelayed || _disposed) return;
    if (creationIntent == null) {
      if (subject.trim().length < 3 ||
          subject.length > 200 ||
          body.trim().isEmpty ||
          body.length > 8000 ||
          !ticketCategories.contains(category) ||
          !ticketPriorities.contains(priority)) {
        return;
      }
      creationIntent = Map.unmodifiable({
        'request_id': uuid(),
        'category': category,
        'priority': priority,
        'subject': subject,
        'body': body,
      });
    }
    busy = true;
    failure = null;
    notifyListeners();
    try {
      final result = await repository.create(organizationId, creationIntent!);
      if (_disposed) return;
      ticket = result;
      subject = '';
      body = '';
      creationIntent = null;
      requiresReadback = false;
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e, command: true);
        recordFailure(failure!);
        requiresReadback = failure!.uncertain;
        if (!requiresReadback && failure!.kind == ApiFailureKind.validation) {
          creationIntent = null;
        }
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
    if (!_disposed && failure == null && ticket != null) await open(ticket!.id);
  }

  Future<void> send({List<String> fileIds = const []}) async {
    if (busy ||
        retryDelayed ||
        _disposed ||
        requiresReadback ||
        ticket == null ||
        ticket!.status == 'closed') {
      return;
    }
    busy = true;
    uncertainScope = 'reply';
    failure = null;
    notifyListeners();
    try {
      final result = await repository.reply(
        organizationId,
        ticket!,
        reply,
        fileIds: fileIds,
        legacyText: legacyText,
      );
      if (_disposed) return;
      ticket = result;
      reply = '';
      legacyText = '';
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e, command: true);
        recordFailure(failure!);
        requiresReadback =
            failure!.uncertain || failure!.kind == ApiFailureKind.conflict;
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
    if (!_disposed && failure == null) await open(ticket!.id);
  }

  Future<void> changeStatus({required bool reopen}) async {
    if (busy ||
        retryDelayed ||
        _disposed ||
        requiresReadback ||
        ticket == null) {
      return;
    }
    busy = true;
    uncertainScope = 'status';
    failure = null;
    notifyListeners();
    try {
      final result = await repository.status(
        organizationId,
        ticket!,
        reason,
        reopen: reopen,
      );
      if (_disposed) return;
      ticket = result;
      reason = '';
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e, command: true);
        recordFailure(failure!);
        requiresReadback =
            failure!.uncertain || failure!.kind == ApiFailureKind.conflict;
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
    if (!_disposed && failure == null) await open(ticket!.id);
  }

  Future<void> loadNotices({bool more = false}) async {
    if (busy || retryDelayed || _disposed) return;
    busy = true;
    failure = null;
    notifyListeners();
    try {
      final batch = await repository.notices(
        organizationId,
        cursor: more ? noticeCursor : null,
      );
      final pref = await repository.preference(organizationId);
      if (_disposed) return;
      notices = more ? [...notices, ...batch.items] : batch.items;
      noticeCursor = batch.cursor;
      preference = pref;
      if (uncertainScope == 'preference' || uncertainScope == 'notice') {
        requiresReadback = false;
        uncertainScope = null;
      }
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e);
        recordFailure(failure!);
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<void> setPreference(bool value) async {
    if (busy ||
        retryDelayed ||
        _disposed ||
        preference == null ||
        requiresReadback) {
      return;
    }
    busy = true;
    uncertainScope = 'preference';
    failure = null;
    notifyListeners();
    try {
      final result = await repository.setPreference(
        organizationId,
        preference!,
        value,
      );
      if (!_disposed) preference = result;
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e, command: true);
        recordFailure(failure!);
        requiresReadback =
            failure!.uncertain || failure!.kind == ApiFailureKind.conflict;
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<void> openNotice(SupportNotice notice) async {
    if (busy || retryDelayed || _disposed) return;
    busy = true;
    uncertainScope = 'notice';
    failure = null;
    notifyListeners();
    try {
      await repository.readNotice(organizationId, notice);
    } catch (e) {
      if (!_disposed) {
        failure = failureOf(e, command: true);
        recordFailure(failure!);
        requiresReadback = failure!.uncertain;
      }
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
    if (!_disposed && failure == null) await open(notice.ticketId);
  }

  @override
  void dispose() {
    _disposed = true;
    _generation++;
    ticket = null;
    messages = [];
    history = [];
    tickets = [];
    notices = [];
    subject = '';
    body = '';
    reply = '';
    reason = '';
    legacyText = '';
    creationIntent = null;
    super.dispose();
  }
}
