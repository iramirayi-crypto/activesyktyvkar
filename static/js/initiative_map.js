document.addEventListener("DOMContentLoaded", () => {
    if (typeof L === "undefined") {
        return;
    }

    const syktyvkarCenter = [61.6688, 50.8353];
    let lastNominatimRequestAt = 0;

    const requestNominatim = async (url) => {
        const wait = Math.max(0, 1100 - (Date.now() - lastNominatimRequestAt));
        if (wait) {
            await new Promise((resolve) => window.setTimeout(resolve, wait));
        }
        lastNominatimRequestAt = Date.now();
        const response = await fetch(url, {
            headers: { Accept: "application/json" },
        });
        if (!response.ok) {
            throw new Error("Nominatim request failed");
        }
        return response.json();
    };

    const formatAddress = (result) => {
        const address = result?.address || {};
        const road = (
            address.road
            || address.pedestrian
            || address.residential
            || address.footway
            || address.path
        );
        const normalizedRoad = road?.replace(/^улица\s+/i, "ул. ");
        const objectName = (
            result?.name
            || address.amenity
            || address.leisure
            || address.tourism
        );
        const city = address.city || address.town || address.municipality || "Сыктывкар";
        const parts = [];

        if (normalizedRoad) {
            parts.push(
                address.house_number
                    ? `${normalizedRoad}, ${address.house_number}`
                    : normalizedRoad
            );
        } else if (objectName) {
            parts.push(objectName);
        } else if (result?.display_name) {
            parts.push(...result.display_name.split(",").slice(0, 3));
        }

        if (city && !parts.some((part) => part.trim().toLowerCase() === city.toLowerCase())) {
            parts.push(city);
        }

        return parts.map((part) => part.trim()).filter(Boolean).join(", ").slice(0, 500);
    };

    document.querySelectorAll("[data-initiative-map]").forEach((mapElement) => {
        const locationInput = mapElement.dataset.locationInput
            ? document.getElementById(mapElement.dataset.locationInput)
            : null;

        const latitudeInput = mapElement.dataset.latitudeInput
            ? document.getElementById(mapElement.dataset.latitudeInput)
            : null;

        const longitudeInput = mapElement.dataset.longitudeInput
            ? document.getElementById(mapElement.dataset.longitudeInput)
            : null;

        const rawLatitude = latitudeInput?.value || mapElement.dataset.latitude;
        const rawLongitude = longitudeInput?.value || mapElement.dataset.longitude;

        const latitude = Number.parseFloat(rawLatitude);
        const longitude = Number.parseFloat(rawLongitude);

        const hasCoordinates = (
            Number.isFinite(latitude)
            && latitude >= -90
            && latitude <= 90
            && Number.isFinite(longitude)
            && longitude >= -180
            && longitude <= 180
        );

        const initialCenter = hasCoordinates
            ? [latitude, longitude]
            : syktyvkarCenter;

        const map = L.map(mapElement).setView(
            initialCenter,
            hasCoordinates ? 15 : 12
        );

        let marker = null;
        let geocodingSequence = 0;

        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(map);

        if (hasCoordinates) {
            marker = L.marker(initialCenter).addTo(map);
        }

        if (latitudeInput && longitudeInput) {
            map.on("click", async (event) => {
                const coordinates = event.latlng;
                const requestSequence = ++geocodingSequence;

                if (marker) {
                    marker.setLatLng(coordinates);
                } else {
                    marker = L.marker(coordinates).addTo(map);
                }

                latitudeInput.value = coordinates.lat.toFixed(6);
                longitudeInput.value = coordinates.lng.toFixed(6);

                mapElement.classList.remove("is-invalid");

                mapElement.parentElement
                    ?.querySelectorAll(".invalid-feedback")
                    .forEach((feedback) => feedback.remove());

                if (!locationInput) {
                    return;
                }

                const previousValue = locationInput.value;

                try {
                    const params = new URLSearchParams({
                        format: "jsonv2",
                        lat: coordinates.lat,
                        lon: coordinates.lng,
                        zoom: "18",
                        addressdetails: "1",
                        "accept-language": "ru",
                    });
                    const data = await requestNominatim(
                        `https://nominatim.openstreetmap.org/reverse?${params}`
                    );
                    const address = formatAddress(data);

                    if (
                        address
                        && requestSequence === geocodingSequence
                        && locationInput.value === previousValue
                    ) {
                        locationInput.value = address;
                    }
                } catch (error) {
                    console.warn("Не удалось определить адрес через Nominatim.");
                }
            });

            locationInput?.addEventListener("blur", async () => {
                const userLocation = locationInput.value.trim();
                if (!userLocation) {
                    return;
                }

                const requestSequence = ++geocodingSequence;
                const query = /сыктывкар/i.test(userLocation)
                    ? userLocation
                    : `${userLocation}, Сыктывкар`;

                try {
                    const params = new URLSearchParams({
                        format: "jsonv2",
                        q: query,
                        limit: "1",
                        countrycodes: "ru",
                        viewbox: "50.68,61.78,51.05,61.55",
                        addressdetails: "1",
                        "accept-language": "ru",
                    });
                    const results = await requestNominatim(
                        `https://nominatim.openstreetmap.org/search?${params}`
                    );
                    const result = results[0];
                    const foundLatitude = Number.parseFloat(result?.lat);
                    const foundLongitude = Number.parseFloat(result?.lon);

                    if (
                        requestSequence !== geocodingSequence
                        || !Number.isFinite(foundLatitude)
                        || !Number.isFinite(foundLongitude)
                    ) {
                        return;
                    }

                    const coordinates = [foundLatitude, foundLongitude];
                    if (marker) {
                        marker.setLatLng(coordinates);
                    } else {
                        marker = L.marker(coordinates).addTo(map);
                    }
                    map.setView(coordinates, 16);
                    latitudeInput.value = foundLatitude.toFixed(6);
                    longitudeInput.value = foundLongitude.toFixed(6);
                } catch (error) {
                    console.warn("Не удалось найти адрес через Nominatim.");
                }
            });
        }
    });
});
