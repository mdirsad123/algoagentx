"use client";

import {
  User,
  FileText,
  Users,
  Building2,
  Info,
  X,
  Download,
  Eye,
} from "lucide-react";
import { useState } from "react";

const ImageModal = ({
  src,
  alt,
  onClose,
}: {
  src: string;
  alt: string;
  onClose: () => void;
}) => {
  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="relative max-w-5xl max-h-[90vh] bg-white rounded-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 bg-white rounded-full p-2 shadow-lg hover:bg-gray-100 z-10"
        >
          <X size={24} />
        </button>
        <img
          src={src}
          alt={alt}
          className="max-w-full max-h-[90vh] object-contain"
        />
      </div>
    </div>
  );
};

const DocumentViewer = ({ url, label }: { url: string; label: string }) => {
  const [showModal, setShowModal] = useState(false);

  if (!url) return null;

  // Helper function to construct full URL
  const getFullUrl = (path: string) => {
    if (!path) return "";
    if (path.startsWith("http")) return path;

    const baseUrl = "http://localhost:4000";
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    return `${baseUrl}${cleanPath}`;
  };

  const fullUrl = getFullUrl(url);
  const isImage = /\.(jpg|jpeg|png|gif|bmp|webp)$/i.test(url);
  const isPDF = /\.pdf$/i.test(url);

  return (
    <>
      <div className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
        <FileText size={20} className="text-blue-500" />
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
            {label}
          </p>
        </div>
        <div className="flex gap-2">
          {isImage && (
            <button
              onClick={() => setShowModal(true)}
              className="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded flex items-center gap-1"
            >
              <Eye size={16} />
              View
            </button>
          )}
          {isPDF && (
            <a
              href={fullUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1 bg-green-500 hover:bg-green-600 text-white text-sm rounded flex items-center gap-1"
            >
              <FileText size={16} />
              Open PDF
            </a>
          )}
          <a
            href={fullUrl}
            download
            className="px-3 py-1 bg-gray-500 hover:bg-gray-600 text-white text-sm rounded flex items-center gap-1"
          >
            <Download size={16} />
            Download
          </a>
        </div>
      </div>

      {showModal && isImage && (
        <ImageModal
          src={fullUrl}
          alt={label}
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  );
};

const DriverViewDetails = ({
  data,
  onPrint,
}: {
  data: any;
  onPrint?: () => void;
}) => {
  const [showDriverImage, setShowDriverImage] = useState(false);

  if (!data) return null;

  // Helper function to construct full URL
  const getFullUrl = (path: string) => {
    if (!path) return "";
    if (path.startsWith("http")) return path;

    const baseUrl = "http://localhost:4000";
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    return `${baseUrl}${cleanPath}`;
  };

  const personal = data.personal || {};
  const documents = data.documents?.[0] || {};
  const nominees = data.nominees || [];
  const bank = data.bank?.[0] || {};
  const info = data.info || {};

  return (
    <div className="bg-white dark:bg-gray-900 p-6 rounded-lg space-y-6">
      {/* ================= HEADER ================= */}
      <div className="pb-4 flex items-start justify-between gap-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-start gap-4">
          {/* Driver Photo */}
          {/* Driver Photo */}
          {personal.driver_img ? (
            <div className="relative group">
              <img
                src={getFullUrl(personal.driver_img)}
                alt={personal.driver_name}
                className="w-24 h-24 rounded-full object-cover border-4 border-blue-500 cursor-pointer hover:opacity-80 transition-opacity"
                onClick={() => setShowDriverImage(true)}
              />
              <div
                className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                onClick={() => setShowDriverImage(true)}
              >
                <Eye className="text-white drop-shadow-lg" size={32} />
              </div>
            </div>
          ) : (
            <div className="text-blue-500 text-3xl mt-1">
              <User size={40} />
            </div>
          )}
          <div>
            <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
              {personal.driver_name}
            </h1>

            <p className="text-sm text-gray-500 mt-1">
              Driver Code:{" "}
              <span className="font-semibold">{personal.driver_code}</span>
            </p>

            <div className="flex gap-2 mt-2">
              <span className="inline-block px-3 py-1 text-sm rounded bg-blue-600 text-white">
                {personal.status}
              </span>
              <span className="inline-block px-3 py-1 text-sm rounded bg-gray-200 text-gray-700">
                {personal.martial_status}
              </span>
            </div>
          </div>
        </div>

        {/* Print button */}
        {onPrint && (
          <div className="print:hidden no-print">
            <button
              onClick={onPrint}
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded shadow whitespace-nowrap"
            >
              Print Driver Details
            </button>
          </div>
        )}
      </div>

      {/* Driver Image Modal */}
      {showDriverImage && personal.driver_img && (
        <ImageModal
          src={getFullUrl(personal.driver_img)}
          alt={personal.driver_name}
          onClose={() => setShowDriverImage(false)}
        />
      )}

      {/* ================= PERSONAL INFORMATION ================= */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4">
          <User className="text-blue-500" size={24} />
          <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-200">
            Personal Information
          </h2>
        </div>

        <div className="grid grid-cols-3 gap-4 text-sm text-gray-700 dark:text-gray-200">
          <div>
            <strong>Gender:</strong> {personal.gender}
          </div>
          <div>
            <strong>Age:</strong> {personal.age}
          </div>
          <div>
            <strong>Date of Birth:</strong>{" "}
            {personal.date_of_birth
              ? new Date(personal.date_of_birth).toLocaleDateString("en-GB")
              : "N/A"}
          </div>
          <div>
            <strong>Mobile No:</strong> {personal.mobile_no}
          </div>
          <div>
            <strong>Email:</strong> {personal.email || "N/A"}
          </div>
          <div>
            <strong>Blood Group:</strong> {personal.blood_group}
          </div>
          <div>
            <strong>Height:</strong> {personal.height || "N/A"}
          </div>
          <div>
            <strong>Weight:</strong> {personal.weight || "N/A"}
          </div>
          <div>
            <strong>Eye Colour:</strong> {personal.eye_colour}
          </div>
          <div>
            <strong>Hair Colour:</strong> {personal.hair_colour}
          </div>
          <div>
            <strong>Nationality:</strong> {personal.nationlaity}
          </div>
          <div>
            <strong>Religion:</strong> {personal.religion}
          </div>
          <div>
            <strong>Birth Place:</strong> {personal.birth_place}
          </div>
          <div>
            <strong>Domicile State:</strong> {personal.domicile_state}
          </div>
          <div>
            <strong>Education Status:</strong> {personal.education_status}
          </div>
          <div>
            <strong>PAN No:</strong> {personal.pan_no}
          </div>
          <div>
            <strong>Aadhaar No:</strong> {personal.adhar_no}
          </div>
          <div>
            <strong>Visible ID Mark:</strong> {personal.visible_id_mark}
          </div>
          <div className="col-span-3">
            <strong>Permanent Address:</strong> {personal.param_address}
          </div>
          <div>
            <strong>City:</strong> {personal.city}
          </div>
          <div>
            <strong>State:</strong> {personal.state}
          </div>
          <div>
            <strong>Country:</strong> {personal.country}
          </div>
          <div>
            <strong>District:</strong> {personal.district}
          </div>
          <div>
            <strong>Taluka:</strong> {personal.taluka}
          </div>
          <div>
            <strong>Joining Date:</strong>{" "}
            {personal.joining_date
              ? new Date(personal.joining_date).toLocaleDateString("en-GB")
              : "N/A"}
          </div>
          <div>
            <strong>Driving Experience:</strong> {personal.driving_exp}
          </div>
          <div>
            <strong>Previous Employed:</strong> {personal.prev_employed}
          </div>
          <div>
            <strong>Present Profession:</strong> {personal.present_profession}
          </div>
        </div>

        {/* Aadhaar Document */}
        {personal.adhar_doc && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-md font-semibold mb-3 text-gray-700 dark:text-gray-200">
              Identity Documents
            </h3>
            <DocumentViewer url={personal.adhar_doc} label="Aadhaar Card" />
          </div>
        )}

        {/* Present Address */}
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <h3 className="text-md font-semibold mb-3 text-gray-700 dark:text-gray-200">
            Present Address
          </h3>
          <div className="grid grid-cols-3 gap-4 text-sm text-gray-700 dark:text-gray-200">
            <div className="col-span-3">
              <strong>Address:</strong> {personal.present_address}
            </div>
            <div>
              <strong>City:</strong> {personal.present_city}
            </div>
            <div>
              <strong>State:</strong> {personal.present_state}
            </div>
            <div>
              <strong>Country:</strong> {personal.present_country}
            </div>
            <div>
              <strong>District:</strong> {personal.present_district}
            </div>
            <div>
              <strong>Taluka:</strong> {personal.present_taluka}
            </div>
            <div>
              <strong>Mobile No:</strong> {personal.present_mobile_no}
            </div>
          </div>
        </div>
      </div>

      {/* ================= DOCUMENTS (LICENSE) ================= */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="text-green-500" size={24} />
          <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-200">
            License & Documents
          </h2>
        </div>

        <div className="space-y-4">
          {/* License Information */}
          <div>
            <h3 className="text-md font-semibold mb-3 text-gray-700 dark:text-gray-200">
              License Information
            </h3>
            <div className="grid grid-cols-3 gap-4 text-sm text-gray-700 dark:text-gray-200 mb-4">
              <div>
                <strong>License No:</strong> {documents.license_no}
              </div>
              <div>
                <strong>Issue Authority:</strong> {documents.issue_authourity}
              </div>
              <div>
                <strong>Issue Date:</strong>{" "}
                {documents.license_iisue_date
                  ? new Date(documents.license_iisue_date).toLocaleDateString(
                      "en-GB"
                    )
                  : "N/A"}
              </div>
              <div>
                <strong>Expiry Date:</strong>{" "}
                {documents.license_expiry_date
                  ? new Date(documents.license_expiry_date).toLocaleDateString(
                      "en-GB"
                    )
                  : "N/A"}
              </div>
              <div className="col-span-2">
                <strong>Issue Address:</strong>{" "}
                {documents.license_issue_address}
              </div>
              <div>
                <strong>Issue District:</strong>{" "}
                {documents.license_iisue_district}
              </div>
              <div>
                <strong>Issue State:</strong> {documents.license_iisue_state}
              </div>
              <div>
                <strong>License Expense:</strong> {documents.license_expense}
              </div>
            </div>

            {/* License Document */}
            {documents.license_doc && (
              <DocumentViewer
                url={documents.license_doc}
                label="Driving License"
              />
            )}
          </div>

          {/* Endorsement Information */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-md font-semibold mb-3 text-gray-700 dark:text-gray-200">
              Endorsement Information
            </h3>
            <div className="grid grid-cols-3 gap-4 text-sm text-gray-700 dark:text-gray-200 mb-4">
              <div>
                <strong>Endorsement No:</strong> {documents.endorsement_no}
              </div>
              <div>
                <strong>Issue Authority:</strong>{" "}
                {documents.endorsement_issue_authority}
              </div>
              <div>
                <strong>Issue Date:</strong>{" "}
                {documents.endorsement_issue_date
                  ? new Date(
                      documents.endorsement_issue_date
                    ).toLocaleDateString("en-GB")
                  : "N/A"}
              </div>
              <div>
                <strong>Expire Date:</strong>{" "}
                {documents.endorsement_expire_date
                  ? new Date(
                      documents.endorsement_expire_date
                    ).toLocaleDateString("en-GB")
                  : "N/A"}
              </div>
              <div className="col-span-2">
                <strong>Address:</strong> {documents.endorsement_address}
              </div>
              <div>
                <strong>District:</strong> {documents.endorsement_district}
              </div>
            </div>

            {/* Endorsement Document */}
            {documents.endorsement_doc && (
              <DocumentViewer
                url={documents.endorsement_doc}
                label="Endorsement Certificate"
              />
            )}
          </div>

          {/* Hazardous Material Information */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-md font-semibold mb-3 text-gray-700 dark:text-gray-200">
              Hazardous Material Information
            </h3>
            <div className="grid grid-cols-3 gap-4 text-sm text-gray-700 dark:text-gray-200 mb-4">
              <div>
                <strong>Hazardous No:</strong> {documents.harzardous_no}
              </div>
              <div>
                <strong>Issue Authority:</strong>{" "}
                {documents.hrds_issue_authority}
              </div>
              <div>
                <strong>Issue Date:</strong>{" "}
                {documents.hrds_issue_date
                  ? new Date(documents.hrds_issue_date).toLocaleDateString(
                      "en-GB"
                    )
                  : "N/A"}
              </div>
              <div>
                <strong>Expire Date:</strong>{" "}
                {documents.hrds_expire_date
                  ? new Date(documents.hrds_expire_date).toLocaleDateString(
                      "en-GB"
                    )
                  : "N/A"}
              </div>
              <div className="col-span-3">
                <strong>Address:</strong> {documents.hrds_address}
              </div>
            </div>

            {/* Hazardous Document */}
            {documents.hrds_doc && (
              <DocumentViewer
                url={documents.hrds_doc}
                label="Hazardous Material Certificate"
              />
            )}
          </div>
        </div>
      </div>

      {/* ================= NOMINEES ================= */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4">
          <Users className="text-purple-500" size={24} />
          <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-200">
            Nominee Details
          </h2>
        </div>

        {nominees.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead className="bg-gray-100 dark:bg-gray-800">
                <tr>
                  <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left">
                    Name
                  </th>
                  <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left">
                    Relation
                  </th>
                  <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left">
                    Mobile No
                  </th>
                  <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left">
                    Aadhaar No
                  </th>
                  <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left">
                    Status
                  </th>
                  <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left">
                    Document
                  </th>
                </tr>
              </thead>
              <tbody>
                {nominees.map((nominee: any, index: number) => (
                  <tr key={nominee.nominee_id || index}>
                    <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
                      {nominee.name}
                    </td>
                    <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
                      {nominee.relation}
                    </td>
                    <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
                      {nominee.mobile_no}
                    </td>
                    <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
                      {nominee.aadhaar_no || "N/A"}
                    </td>
                    <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
                      {nominee.status}
                    </td>
                    <td className="border border-gray-300 dark:border-gray-600 px-3 py-2">
                      {nominee.aadhaar_doc ? (
                        <DocumentViewer
                          url={nominee.aadhaar_doc}
                          label={`${nominee.name}'s Aadhaar`}
                        />
                      ) : (
                        <span className="text-gray-400 text-xs">
                          No document
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-sm">No nominees added</p>
        )}
      </div>

      {/* ================= BANK DETAILS ================= */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4">
          <Building2 className="text-orange-500" size={24} />
          <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-200">
            Bank Details
          </h2>
        </div>

        <div className="grid grid-cols-3 gap-4 text-sm text-gray-700 dark:text-gray-200">
          <div>
            <strong>Bank Name:</strong> {bank.driver_bank_name}
          </div>
          <div>
            <strong>Branch Name:</strong> {bank.driver_bank_branch_name}
          </div>
          <div>
            <strong>Account No:</strong> {bank.driver_bank_acc_no}
          </div>
          <div>
            <strong>IFSC Code:</strong> {bank.driver_ifsc_code}
          </div>
          <div>
            <strong>MICR No:</strong> {bank.driver_micr_no}
          </div>
          <div>
            <strong>Status:</strong> {bank.status}
          </div>
          <div className="col-span-3">
            <strong>Bank Address:</strong> {bank.driver_bank_address}
          </div>
        </div>
      </div>

      {/* ================= ADDITIONAL INFORMATION ================= */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4">
          <Info className="text-red-500" size={24} />
          <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-200">
            Additional Information
          </h2>
        </div>

        <div className="space-y-4">
          {/* Emergency Contact */}
          <div>
            <h3 className="text-md font-semibold mb-3 text-gray-700 dark:text-gray-200">
              Emergency Contact
            </h3>
            <div className="grid grid-cols-3 gap-4 text-sm text-gray-700 dark:text-gray-200">
              <div>
                <strong>Name:</strong> {info.to_inform_name}
              </div>
              <div>
                <strong>Mobile No:</strong> {info.to_inform_mobile_no}
              </div>
              <div>
                <strong>Relationship:</strong> {info.to_inform_relationship}
              </div>
              <div className="col-span-3">
                <strong>Address:</strong> {info.to_inform_address}
              </div>
            </div>
          </div>

          {/* Employment History */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-md font-semibold mb-3 text-gray-700 dark:text-gray-200">
              Employment History
            </h3>
            <div className="grid grid-cols-3 gap-4 text-sm text-gray-700 dark:text-gray-200">
              <div>
                <strong>Past Employer:</strong> {info.past_emp}
              </div>
              <div>
                <strong>Past Employer Name:</strong> {info.past_emp_name}
              </div>
              <div>
                <strong>Last Employment Date:</strong>{" "}
                {info.last_emp_date
                  ? new Date(info.last_emp_date).toLocaleDateString("en-GB")
                  : "N/A"}
              </div>
              <div className="col-span-2">
                <strong>Last Employer Address:</strong> {info.last_emp_address}
              </div>
              <div>
                <strong>Last Employer Mobile:</strong> {info.last_emp_mobile}
              </div>
              <div className="col-span-2">
                <strong>Reason for Leaving:</strong> {info.reason_leaving_job}
              </div>
              <div>
                <strong>Leaving Date:</strong>{" "}
                {info.leaving_date
                  ? new Date(info.leaving_date).toLocaleDateString("en-GB")
                  : "N/A"}
              </div>
              <div className="col-span-3">
                <strong>Past History:</strong> {info.past_history}
              </div>
            </div>
          </div>

          {/* Accident Information */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-md font-semibold mb-3 text-gray-700 dark:text-gray-200">
              Accident Information
            </h3>
            <div className="grid grid-cols-3 gap-4 text-sm text-gray-700 dark:text-gray-200">
              <div>
                <strong>Nature of Accident:</strong> {info.nature_of_accident}
              </div>
              <div>
                <strong>Location:</strong> {info.location_of_accident}
              </div>
              <div>
                <strong>Fatalities:</strong> {info.driver_fatalities}
              </div>
              <div className="col-span-3">
                <strong>Injuries:</strong> {info.driver_injury}
              </div>
            </div>
          </div>

          {/* Introducer Information */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-md font-semibold mb-3 text-gray-700 dark:text-gray-200">
              Introducer Information
            </h3>
            <div className="grid grid-cols-3 gap-4 text-sm text-gray-700 dark:text-gray-200">
              <div>
                <strong>Code:</strong> {info.introducer_driver_code}
              </div>
              <div>
                <strong>Name:</strong> {info.introducer_driver_name}
              </div>
              <div>
                <strong>Mobile:</strong> {info.introducer_driver_mobile}
              </div>
              <div className="col-span-3">
                <strong>Address:</strong> {info.introducer_driver_address}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DriverViewDetails;
