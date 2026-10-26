class ApplicationCycle {
  final String id, code, nameEn, nameTa, formId;
  final DateTime opensAt, closesAt;
  ApplicationCycle.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      code = json['code'] as String,
      nameEn = json['name_en'] as String,
      nameTa = json['name_ta'] as String,
      formId = json['form_id'] as String,
      opensAt = DateTime.parse(json['opens_at'] as String),
      closesAt = DateTime.parse(json['closes_at'] as String);
}

class ApplicationField {
  final String id, key, section, labelEn, labelTa, type;
  final bool isRequired;
  final int position;
  ApplicationField.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      key = json['key'] as String,
      section = json['section'] as String,
      labelEn = json['label_en'] as String,
      labelTa = json['label_ta'] as String,
      type = json['field_type'] as String,
      isRequired = json['required'] as bool,
      position = json['position'] as int;
}

class ApplicationAcknowledgement {
  final String id, kind, labelEn, labelTa;
  final bool isRequired;
  ApplicationAcknowledgement.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      kind = json['kind'] as String,
      labelEn = json['label_en'] as String,
      labelTa = json['label_ta'] as String,
      isRequired = json['required'] as bool;
}

class ApplicationDocumentRequirement {
  final String id, policyId, labelEn, labelTa, instructionsEn, instructionsTa;
  final String noticeEn, noticeTa;
  final int minFiles, maxFiles, maxFileBytes, maxUploadBytes, policyMaxFiles;
  final int retentionDays, rejectedRetentionDays;
  final List<String> mimeTypes;
  ApplicationDocumentRequirement.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      policyId = (json['file_policy'] as Map)['id'] as String,
      labelEn = json['label_en'] as String,
      labelTa = json['label_ta'] as String,
      instructionsEn = json['instructions_en'] as String,
      instructionsTa = json['instructions_ta'] as String,
      minFiles = json['min_files'] as int,
      maxFiles = json['max_files'] as int,
      noticeEn = (json['file_policy'] as Map)['notice_en'] as String,
      noticeTa = (json['file_policy'] as Map)['notice_ta'] as String,
      maxFileBytes = (json['file_policy'] as Map)['max_file_bytes'] as int,
      maxUploadBytes = (json['file_policy'] as Map)['max_upload_bytes'] as int,
      policyMaxFiles = (json['file_policy'] as Map)['max_files'] as int,
      retentionDays = (json['file_policy'] as Map)['retention_days'] as int,
      rejectedRetentionDays =
          (json['file_policy'] as Map)['rejected_retention_days'] as int,
      mimeTypes = List.unmodifiable(
        ((json['file_policy'] as Map)['allowed_mime_types'] as List)
            .cast<String>(),
      ) {
    if (minFiles < 0 ||
        maxFiles < 1 ||
        maxFiles > 100 ||
        minFiles > maxFiles ||
        maxFileBytes < 1 ||
        maxUploadBytes < 1 ||
        policyMaxFiles < 1 ||
        policyMaxFiles > 100 ||
        retentionDays < 1 ||
        rejectedRetentionDays < 1 ||
        mimeTypes.isEmpty) {
      throw const FormatException('Invalid document policy');
    }
  }

  /// Operational ceilings can be lower than the pinned collection policy.
  int effectiveUploadLimit(int operationalMaxBytes) => [
    maxFileBytes,
    maxUploadBytes,
    operationalMaxBytes,
  ].reduce((left, right) => left < right ? left : right);
}

class ApplicationForm {
  final String id, organizationId, titleEn, titleTa;
  final int version, maxUploadBytes;
  final bool collectionEnabled;
  final List<ApplicationField> fields;
  final List<ApplicationAcknowledgement> acknowledgements;
  final List<ApplicationDocumentRequirement> documents;
  ApplicationForm.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      organizationId = json['organization_id'] as String,
      titleEn = json['title_en'] as String,
      titleTa = json['title_ta'] as String,
      version = json['version'] as int,
      maxUploadBytes = (json['max_upload_bytes'] as int?) ?? 0,
      collectionEnabled = json['collection_enabled'] == true,
      fields = List.unmodifiable(
        (json['fields'] as List).map(
          (item) => ApplicationField.fromJson(applicationObject(item)),
        ),
      ),
      acknowledgements = List.unmodifiable(
        (json['acknowledgements'] as List).map(
          (item) =>
              ApplicationAcknowledgement.fromJson(applicationObject(item)),
        ),
      ),
      documents = List.unmodifiable(
        ((json['document_requirements'] as List?) ?? const []).map(
          (item) =>
              ApplicationDocumentRequirement.fromJson(applicationObject(item)),
        ),
      );
}

class AcceptedApplicationAcknowledgement {
  final String id;
  final DateTime acceptedAt;
  AcceptedApplicationAcknowledgement.fromJson(Map<String, dynamic> json)
    : id = json['definition_id'] as String,
      acceptedAt = DateTime.parse(json['accepted_at'] as String);
}

class ApplicationStatusEvent {
  final String state;
  final int version;
  final DateTime createdAt;
  ApplicationStatusEvent.fromJson(Map<String, dynamic> json)
    : state = json['to_state'] as String,
      version = json['application_version'] as int,
      createdAt = DateTime.parse(json['created_at'] as String);
}

class ApplicationRecord {
  final String id, state;
  final String? cycleId, number;
  final ApplicationForm form;
  final int version, revision, completionPercent;
  final DateTime updatedAt;
  final DateTime? submittedAt;
  final Map<String, String> answers;
  final List<AcceptedApplicationAcknowledgement> accepted;
  final List<ApplicationStatusEvent> history;
  bool get isDraft => state == 'draft';
  ApplicationRecord.fromJson(Map<String, dynamic> json)
    : id = json['id'] as String,
      cycleId = json['cycle_id'] as String?,
      state = json['state'] as String,
      number = json['application_number'] as String?,
      form = ApplicationForm.fromJson(applicationObject(json['form'])),
      version = json['version'] as int,
      revision = json['revision'] as int,
      completionPercent = json['completion_percent'] as int,
      updatedAt = DateTime.parse(json['updated_at'] as String),
      submittedAt = json['submitted_at'] == null
          ? null
          : DateTime.parse(json['submitted_at'] as String),
      answers = Map.unmodifiable({
        for (final value in json['answers'] as List)
          (value as Map)['field_id'] as String: value['value'] as String,
      }),
      accepted = List.unmodifiable(
        ((json['accepted_acknowledgements'] as List?) ?? const []).map(
          (item) => AcceptedApplicationAcknowledgement.fromJson(
            applicationObject(item),
          ),
        ),
      ),
      history = List.unmodifiable(
        ((json['status_history'] as List?) ?? const []).map(
          (item) => ApplicationStatusEvent.fromJson(applicationObject(item)),
        ),
      );
}

Map<String, dynamic> applicationObject(Object? value) =>
    Map<String, dynamic>.from(value as Map);
