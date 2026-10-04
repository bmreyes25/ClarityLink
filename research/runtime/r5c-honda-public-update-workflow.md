# R5C Honda public update workflow (observed pages only)

Research date: 2026-10-04. This records public documentation, not a portal transaction or vehicle update.

## Consumer USB portal

[Honda's public USB site](https://usb.honda.com/index.html?lang=en) says a vehicle-generated data file is required. It describes selecting `update_by_usb` or `update_by_usb.json` from a `HondaSoftwareUpdates` or `rb` folder, uploading it to check for updates, and downloading a vehicle-matched file if offered. The page displays a VIN field after the search flow but gives no version list, package filename, package structure, receiver inventory, or historical archive to a visitor without the vehicle file. R5C did not submit anything or attempt to infer the request format.

## Dealer firmware downloader

[Honda bulletin 19-101, revision 2](https://static.nhtsa.gov/odi/tsbs/2019/MC-10169058-0001.pdf) directs a shop to use Honda Firmware Downloader with the vehicle's VIN. It identifies the update target as 2016–17 Civic 2-door and 4-door EX, EX-T, and Touring, with resulting software versions `1.F197.60` (2016) and `1.F196.39` (2017). It gives failed-part number `39101-TBA-A21` and warns that year/trim-specific software matters. The public bulletin does not disclose a download URL, filename, hash, or package contents. The [earlier revision](https://static.nhtsa.gov/odi/tsbs/2019/MC-10166786-0001.pdf) corroborates the same version mapping. [Bulletin 16-100](https://static.nhtsa.gov/odi/tsbs/2017/SB-10108290-9340.pdf) documents an earlier 2017 Civic dealer USB update and excludes hatchbacks; it does not provide a versioned receiver archive.

The consumer USB portal and dealer firmware downloader are distinct publicly described channels; neither yielded an R5C payload. No credentialed dealer software, VIN query, or vehicle data was used.

## Research update naming (not an official portal promise)

The public [ic1101 update notes](https://github.com/librick/ic1101/blob/main/docs/updates.md) describe `SwUpdate.mdt` as a package name and `SwUpdate.txt` / `SwUpdate2.txt` as metadata files in a Civic vcm30t30 update format, with `ro.build.id` and `custom_rom.type` metadata. This is `PUBLIC_RESEARCH` about that family, not an official Honda download link and not evidence that the 19-101 package has been obtained or contains `jmcs`. R5C did not construct, test, or apply an update.
