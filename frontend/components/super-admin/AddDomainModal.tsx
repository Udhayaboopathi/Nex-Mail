"use client";

import { useState } from "react";
import { X, Globe, CheckCircle } from "lucide-react";
import { superAdminApi } from "../../lib/api";
import { toast } from "../ui/Toast";

interface AddDomainModalProps {
  onClose: () => void;
  onAdded: () => void;
}

export function AddDomainModal({ onClose, onAdded }: AddDomainModalProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [domainName, setDomainName] = useState("");
  const [storageQuotaGb, setStorageQuotaGb] = useState("10");
  const [saving, setSaving] = useState(false);
  const [created, setCreated] = useState(false);

  async function handleCreate() {
    if (!domainName.trim()) { toast("Enter a domain name", "error"); return; }
    const q = parseInt(storageQuotaGb, 10);
    if (Number.isNaN(q) || q < 1) { toast("Enter a valid total storage (GB), at least 1.", "error"); return; }
    if (q > 2048) { toast("Maximum domain storage is 2048 GB.", "error"); return; }
    setSaving(true);
    try {
      await superAdminApi.createDomain({
        name: domainName.trim().toLowerCase(),
        storage_quota_gb: q,
      });
      setCreated(true);
      setStep(2);
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Add Domain</h2>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Steps indicator */}
        <div className="flex items-center gap-2 px-6 py-3 border-b border-gray-100 dark:border-gray-800">
          {([1, 2, 3] as const).map((s) => (
            <div key={s} className="flex items-center gap-1">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${step >= s ? "bg-indigo-600 text-white" : "bg-gray-200 dark:bg-gray-700 text-gray-500"}`}>{s}</div>
              {s < 3 && <div className="w-10 h-px bg-gray-200 dark:bg-gray-700" />}
            </div>
          ))}
          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
            {step === 1 ? "Domain Name" : step === 2 ? "DNS Setup" : "Verify"}
          </span>
        </div>

        <div className="px-6 py-6">
          {step === 1 && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 text-sm">
                <Globe className="w-5 h-5 shrink-0" />
                <span>
                  Enter the domain you want to add. A DKIM keypair will be generated automatically. Set the total
                  storage pool (GB) for this domain — the domain admin splits it across mailboxes.
                </span>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Domain name</label>
                <input
                  value={domainName}
                  onChange={(e) => setDomainName(e.target.value)}
                  placeholder="example.com"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Total storage (GB)
                </label>
                <input
                  type="number"
                  min={1}
                  max={2048}
                  value={storageQuotaGb}
                  onChange={(e) => setStorageQuotaGb(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                />
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Domain admin allocates this across all mailboxes.</p>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              {created && (
                <div className="flex items-center gap-2 text-green-600 dark:text-green-400 text-sm">
                  <CheckCircle className="w-5 h-5" />
                  <span>Domain <strong>{domainName}</strong> created! Add the following DNS records:</span>
                </div>
              )}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-2 font-mono text-xs text-gray-700 dark:text-gray-300">
                <p><span className="text-gray-400">MX</span>   @ → mail.{domainName}</p>
                <p><span className="text-gray-400">A</span>    mail → YOUR_SERVER_IP</p>
                <p><span className="text-gray-400">TXT</span>  @ → v=spf1 ip4:YOUR_IP mx ~all</p>
                <p><span className="text-gray-400">TXT</span>  _dmarc → v=DMARC1; p=quarantine; rua=mailto:dmarc@{domainName}</p>
                <p><span className="text-gray-400">TXT</span>  mail._domainkey → v=DKIM1; k=rsa; p=... (see domain detail)</p>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="text-center py-4">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
              <p className="font-medium text-gray-900 dark:text-white">Domain Added!</p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">You can verify DNS from the Domains panel after propagation.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 dark:border-gray-800">
          <button onClick={onClose} className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">Cancel</button>
          <div className="flex gap-2">
            {step > 1 && step < 3 && (
              <button onClick={() => setStep((s) => (s - 1) as 1 | 2 | 3)} className="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">
                Back
              </button>
            )}
            {step === 1 && (
              <button onClick={handleCreate} disabled={saving} className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60">
                {saving ? "Creating…" : "Create Domain"}
              </button>
            )}
            {step === 2 && (
              <button onClick={() => setStep(3)} className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium">
                DNS Added →
              </button>
            )}
            {step === 3 && (
              <button onClick={() => { onAdded(); onClose(); }} className="px-4 py-2 text-sm rounded-lg bg-green-600 hover:bg-green-700 text-white font-medium">
                Done
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
