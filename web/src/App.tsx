import { useEffect, useMemo, useState } from "react";

type BeverageType = "auto" | "spirits" | "beer" | "wine";

type UploadedImage = {
  id: string;
  filename: string;
  content_type: string;
  storage_key: string;
  size_bytes: number;
  preview_url: string;
};

type GroupImage = {
  id: string;
  filename: string;
  storage_key: string;
  preview_url: string;
};

type LabelGroup = {
  label_id: string;
  label_name: string;
  beverage_type: BeverageType;
  images: GroupImage[];
};

type FieldResult = {
  field_name: string;
  status: "pass" | "fail" | "unreadable";
  extracted_value?: string;
  failure_reason?: string;
  cfr_reference?: string;
  found_on_image?: number;
};

type LabelResult = {
  label_id: string;
  label_name: string;
  overall_status: "PASS" | "FAIL" | "ESCALATE" | "RETRY" | "ERROR";
  beverage_type: BeverageType;
  fields: FieldResult[];
  escalation_reason?: string;
  images_processed: number;
};

type BatchEvent = {
  batch_id: string;
  completed: number;
  total: number;
  result: LabelResult;
};

const MAX_BATCH = 100;

function baseLabelName(filename: string): string {
  return filename.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").trim() || "Untitled Label";
}

function suggestedLabelName(images: GroupImage[] | UploadedImage[]): string {
  if (images.length === 0) {
    return "";
  }
  if (images.length === 1) {
    return baseLabelName(images[0].filename);
  }
  return `${baseLabelName(images[0].filename)} +${images.length - 1} image(s)`;
}

export default function App() {
  const [files, setFiles] = useState<FileList | null>(null);
  const [uploaded, setUploaded] = useState<UploadedImage[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [groups, setGroups] = useState<LabelGroup[]>([]);
  const [labelName, setLabelName] = useState("");
  const [labelNameEdited, setLabelNameEdited] = useState(false);
  const [beverageType, setBeverageType] = useState<BeverageType>("auto");

  const [results, setResults] = useState<LabelResult[]>([]);
  const [batchId, setBatchId] = useState<string>("");
  const [completed, setCompleted] = useState(0);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const selectedImages = useMemo(
    () => uploaded.filter((item) => selectedIds.has(item.id)),
    [uploaded, selectedIds]
  );

  const poolImages = useMemo(() => {
    const groupedIds = new Set(groups.flatMap((g) => g.images.map((i) => i.id)));
    return uploaded.filter((item) => !groupedIds.has(item.id));
  }, [uploaded, groups]);

  const groupByLabelId = useMemo(() => {
    const index = new Map<string, LabelGroup>();
    for (const group of groups) {
      index.set(group.label_id, group);
    }
    return index;
  }, [groups]);

  useEffect(() => {
    if (labelNameEdited) {
      return;
    }
    setLabelName(suggestedLabelName(selectedImages));
  }, [selectedImages, labelNameEdited]);

  function toggleSelection(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        if (next.size >= 3) {
          return next;
        }
        next.add(id);
      }
      return next;
    });
  }

  function toGroupImage(img: UploadedImage): GroupImage {
    return {
      id: img.id,
      filename: img.filename,
      storage_key: img.storage_key,
      preview_url: img.preview_url,
    };
  }

  async function uploadFiles() {
    setError("");
    if (!files || files.length === 0) {
      setError("Choose at least one JPEG or PNG image.");
      return;
    }

    const localFiles = Array.from(files);
    const form = new FormData();
    for (const file of localFiles) {
      if (!["image/jpeg", "image/png"].includes(file.type)) {
        setError(`Unsupported file type: ${file.name}. Only JPEG/PNG allowed.`);
        return;
      }
      form.append("files", file);
    }

    const res = await fetch("/upload", { method: "POST", body: form });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.detail ?? "Upload failed");
      return;
    }

    const data = (await res.json()) as Omit<UploadedImage, "preview_url">[];
    const merged: UploadedImage[] = data.map((item, idx) => ({
      ...item,
      preview_url: URL.createObjectURL(localFiles[idx]),
    }));

    setUploaded((prev) => [...prev, ...merged]);
    setFiles(null);
  }

  function createGroup() {
    setError("");
    if (selectedImages.length < 1 || selectedImages.length > 3) {
      setError("Select 1 to 3 images to create a label group.");
      return;
    }
    if (groups.length >= MAX_BATCH) {
      setError("Batch already has 100 labels.");
      return;
    }

    const id = crypto.randomUUID();
    const finalName = labelName.trim() || suggestedLabelName(selectedImages);
    setGroups((prev) => [
      ...prev,
      {
        label_id: id,
        label_name: finalName,
        beverage_type: beverageType,
        images: selectedImages.map(toGroupImage),
      },
    ]);
    setLabelName("");
    setLabelNameEdited(false);
    setSelectedIds(new Set());
  }

  function createSinglesFromPool() {
    setError("");
    if (poolImages.length === 0) {
      setError("No ungrouped images available.");
      return;
    }
    if (groups.length >= MAX_BATCH) {
      setError("Batch already has 100 labels.");
      return;
    }

    const capacity = MAX_BATCH - groups.length;
    const target = poolImages.slice(0, capacity);

    const newGroups: LabelGroup[] = target.map((img) => ({
      label_id: crypto.randomUUID(),
      label_name: baseLabelName(img.filename),
      beverage_type: beverageType,
      images: [toGroupImage(img)],
    }));

    setGroups((prev) => [...prev, ...newGroups]);
    setSelectedIds(new Set());
    setLabelName("");
    setLabelNameEdited(false);
  }

  async function startVerification() {
    setError("");
    setResults([]);
    setBatchId("");
    setCompleted(0);
    setTotal(groups.length);

    if (groups.length === 0) {
      setError("Create at least one label group first.");
      return;
    }

    setBusy(true);
    try {
      const requestLabels = groups.map((group) => ({
        label_id: group.label_id,
        label_name: group.label_name,
        beverage_type: group.beverage_type,
        images: group.images.map((image) => ({
          id: image.id,
          filename: image.filename,
          storage_key: image.storage_key,
        })),
      }));

      const response = await fetch("/verify/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ labels: requestLabels }),
      });

      if (!response.ok || !response.body) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail ?? "Verification failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const block of parts) {
          const dataLine = block
            .split("\n")
            .find((line) => line.startsWith("data: "));
          if (!dataLine) {
            continue;
          }

          const payload = dataLine.replace("data: ", "").trim();
          if (payload === "done") {
            continue;
          }

          const event = JSON.parse(payload) as BatchEvent;
          setBatchId(event.batch_id);
          setCompleted(event.completed);
          setTotal(event.total);
          setResults((prev) => [event.result, ...prev]);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  }

  function removeGroup(id: string) {
    setGroups((prev) => prev.filter((g) => g.label_id !== id));
  }

  function removeUngroupedImage(id: string) {
    setUploaded((prev) => prev.filter((img) => img.id !== id));
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }

  function removeResult(labelId: string) {
    setResults((prev) => prev.filter((result) => result.label_id !== labelId));
  }

  const exportUrl = batchId ? `/verify/batch/${batchId}/export.csv` : "";

  return (
    <main className="page">
      <section className="panel">
        <h1>TTB Label Verifier</h1>
        <p className="subtitle">JPEG/PNG only. Group 1-3 images per product. Max 100 labels.</p>

        <div className="row">
          <input
            type="file"
            accept="image/jpeg,image/png"
            multiple
            onChange={(e) => setFiles(e.target.files)}
          />
          <button onClick={uploadFiles}>Upload</button>
        </div>

        <h3>Ungrouped Uploads ({poolImages.length})</h3>
        <div className="grid">
          {poolImages.map((img) => (
            <label key={img.id} className="chip">
              <input
                type="checkbox"
                checked={selectedIds.has(img.id)}
                onChange={() => toggleSelection(img.id)}
              />
              <img src={img.preview_url} alt={img.filename} className="thumb" />
              <span>{img.filename}</span>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  removeUngroupedImage(img.id);
                }}
              >
                Remove
              </button>
            </label>
          ))}
        </div>

        <div className="row">
          <input
            placeholder="Label name (auto-filled)"
            value={labelName}
            onChange={(e) => {
              setLabelName(e.target.value);
              setLabelNameEdited(true);
            }}
          />
          <select value={beverageType} onChange={(e) => setBeverageType(e.target.value as BeverageType)}>
            <option value="auto">Auto-detect (Recommended)</option>
            <option value="spirits">Distilled Spirits</option>
            <option value="beer">Beer / Malt Beverage</option>
            <option value="wine">Wine (7%+ ABV)</option>
          </select>
          <button onClick={createGroup}>Create Group ({selectedImages.length})</button>
          <button onClick={createSinglesFromPool}>Create Singles for All</button>
        </div>

        <h3>Batch Groups ({groups.length})</h3>
        <div className="grid">
          {groups.map((g) => (
            <article key={g.label_id} className="group-card">
              <header>
                <strong>{g.label_name}</strong>
                <button onClick={() => removeGroup(g.label_id)}>Remove Group</button>
              </header>
              <div>{g.beverage_type}</div>
              <div className="thumb-row">
                {g.images.map((img) => (
                  <img key={img.id} src={img.preview_url} alt={img.filename} className="thumb" title={img.filename} />
                ))}
              </div>
              <small>{g.images.map((i) => i.filename).join(", ")}</small>
            </article>
          ))}
        </div>

        <div className="row">
          <button disabled={busy || groups.length === 0} onClick={startVerification}>
            {busy ? "Verifying..." : "Verify Batch"}
          </button>
          <div className="progress">
            {completed} of {total} processed
          </div>
          {batchId ? (
            <a href={exportUrl} className="button-link">
              Export CSV
            </a>
          ) : null}
        </div>

        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="panel results">
        <h2>Streamed Results</h2>
        {results.length === 0 ? <p>No results yet.</p> : null}
        {results.map((result, idx) => {
          const group = groupByLabelId.get(result.label_id);
          return (
            <article key={`${result.label_id}-${idx}`} className="result-card">
              <header>
                <strong>{result.label_name}</strong>
                <div className="row">
                  <span className={`status ${result.overall_status.toLowerCase()}`}>{result.overall_status}</span>
                  <button type="button" onClick={() => removeResult(result.label_id)}>
                    Remove
                  </button>
                </div>
              </header>
              <div className="meta">{result.beverage_type} • {result.images_processed} images</div>
              {group ? (
                <div className="result-image-row">
                  {group.images.map((img) => (
                    <img
                      key={img.id}
                      src={img.preview_url}
                      alt={img.filename}
                      className="result-image"
                      title={img.filename}
                    />
                  ))}
                </div>
              ) : null}
              {result.escalation_reason ? <p className="warn">{result.escalation_reason}</p> : null}
              <ul className="fields-list">
                {result.fields.map((f, fieldIdx) => (
                  <li key={`${f.field_name}-${fieldIdx}`}>
                    <span>{f.field_name}</span>
                    <span>{f.status}</span>
                    <span>{f.extracted_value ?? ""}</span>
                    <span>{f.failure_reason ?? ""}</span>
                    <span>{f.cfr_reference ?? ""}</span>
                  </li>
                ))}
              </ul>
            </article>
          );
        })}
      </section>
    </main>
  );
}
